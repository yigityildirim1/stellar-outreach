"""
NEXUS STATION - Stellar Outreach: Push Notification System (TASK-006)

Generates notification content with Co-Star-style voice, manages scheduling
rules, tracks notification history, and handles player preferences.

The actual push delivery (Firebase Cloud Messaging) would be integrated
later in production. This module provides:
    - Content generation (morning briefings, event triggers, re-engagement)
    - Scheduling logic with hard limits (max 2/day, quiet hours, cooldowns)
    - Per-category preference toggles
    - Notification history and tracking

Voice guidelines (GDD §8):
    - lowercase always, no exclamation marks, no caps
    - poetic, blunt, sometimes funny, always personal
    - cryptic space station AI that sees through you
    - never corporate, never cheerful, never fake

References:
    - GDD §8: Push notification system
    - transit_engine.py: Cosmic status integration (POWER/TROUBLE/PRESSURE)

Security Note (Article II / Kai Chen review):
    [KAI] Notification preferences and history are stored per-player in
    sanitized filesystem paths. No PII beyond player_id is stored.
    Quiet hours and timezone are player-controlled. No covert channels.

UX Note (Marina Okonkwo review):
    [MARINA] Hard rules: max 2 notifications/day, never during quiet hours,
    easy granular opt-out, never guilt-trip, no fake urgency. Re-engagement
    only after 3+ days, max 1x/week. Every message should feel like it was
    written just for the player.
"""

from __future__ import annotations

import hashlib
import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, time, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ────────────────────────────────────────────────────────────────
# Persistence Configuration
# ────────────────────────────────────────────────────────────────

PREFS_DIR = Path.home() / ".nexus_station" / "notification_prefs"
HISTORY_DIR = Path.home() / ".nexus_station" / "notification_history"


# ────────────────────────────────────────────────────────────────
# Data Models
# ────────────────────────────────────────────────────────────────

@dataclass
class NotificationPayload:
    """A single notification ready for delivery."""
    id: str                             # UUID
    player_id: str
    category: str                       # "morning_briefing", "event_trigger", "re_engagement"
    title: str                          # Short title for notification header
    body: str                           # The main message text (Co-Star style)
    module_id: Optional[str]            # Which module this relates to, if any
    cosmic_status: Optional[str]        # POWER / TROUBLE / PRESSURE
    event_type: Optional[str]           # For event triggers: "full_moon", etc.
    scheduled_time: str                 # ISO timestamp when this should be sent
    sent: bool
    read: bool
    created_at: str


@dataclass
class NotificationPreferences:
    """Per-player notification settings."""
    player_id: str
    enabled: bool                       # Master toggle
    morning_briefing: bool              # Per-category toggles
    event_triggers: bool
    re_engagement: bool
    quiet_hours_start: str              # "22:00" — default 10 PM
    quiet_hours_end: str                # "08:00" — default 8 AM
    preferred_briefing_time: str        # "08:00" — when to send morning briefing
    timezone: str                       # e.g. "Europe/Istanbul"
    last_active: str                    # ISO timestamp of last app open


@dataclass
class NotificationHistory:
    """Notification history for a player."""
    player_id: str
    notifications: List[NotificationPayload]
    daily_count: Dict[str, int]         # date -> count sent that day


# ────────────────────────────────────────────────────────────────
# Morning Briefing Templates — POWER (3+ per module = 21+)
# ────────────────────────────────────────────────────────────────

POWER_TEMPLATES: Dict[str, List[str]] = {
    "observatory": [
        "power in your observatory today. don't waste it on small questions.",
        "the observatory hums with clarity. every lens is focused.",
        "your research sings today. follow the thread wherever it leads.",
        "the observatory is wide open. the universe is showing you something.",
    ],
    "workshop": [
        "your workshop hums with energy. build something that matters.",
        "the tools feel lighter today. precision comes naturally.",
        "the workshop sparks. everything you touch takes shape.",
        "raw materials bend to your will today. craft boldly.",
    ],
    "commons": [
        "the commons are alive today. your voice carries further than usual.",
        "the commons bloom with connection. someone needs exactly what you offer.",
        "expansion flows through the commons. luck is just preparation meeting today.",
        "the commons doors are open wide. walk through them.",
    ],
    "shrine": [
        "the shrine glows. answers are closer than you think.",
        "your shrine radiates purpose. the core of you is steady.",
        "the shrine burns bright. identity is not a question today.",
        "purpose crystallizes in the shrine. you know who you are.",
    ],
    "quarters": [
        "your quarters run smooth today. let the routine carry you.",
        "the quarters are steady. discipline is easy when the structure holds.",
        "routine becomes ritual today. your quarters are sanctuary.",
        "your quarters hum with quiet power. stability is a superpower.",
    ],
    "greenhouse": [
        "the greenhouse blooms. someone is thinking of you.",
        "love grows easy in the greenhouse today. let it.",
        "the greenhouse overflows. tenderness finds you without trying.",
        "something beautiful is growing in the greenhouse. don't pick it yet.",
    ],
    "bridge": [
        "the bridge is yours today. command with confidence.",
        "your instincts are sharp on the bridge. trust the gut.",
        "the bridge responds to your touch. emotions are fuel today.",
        "the bridge is calm and clear. your feelings are compass needles.",
    ],
}

# ────────────────────────────────────────────────────────────────
# Morning Briefing Templates — TROUBLE (3+ per module = 21+)
# ────────────────────────────────────────────────────────────────

TROUBLE_TEMPLATES: Dict[str, List[str]] = {
    "observatory": [
        "your observatory is foggy today. don't force the insight.",
        "the observatory glass is clouded. some truths need another day.",
        "trouble in the observatory. the data lies today. trust nothing at face value.",
        "the observatory doors stick. not every question deserves today's energy.",
    ],
    "workshop": [
        "the workshop sputters. patience with the process.",
        "trouble in the workshop. the welds won't hold. step back.",
        "the workshop grinds. forcing it makes it worse.",
        "your tools feel heavy today. not every day is for building.",
    ],
    "commons": [
        "the commons are cold. not everyone wants to hear from you today. that's fine.",
        "trouble in the commons. the crowd is restless. don't feed it.",
        "the commons echo with static. connection misfires today.",
        "the commons doors are heavy. some conversations can wait.",
    ],
    "shrine": [
        "the shrine is silent. sometimes that is the answer.",
        "trouble in the shrine. identity wobbles. it will pass.",
        "the shrine light flickers. don't mistake doubt for truth.",
        "the shrine is dim. purpose hides on days like this. it'll return.",
    ],
    "quarters": [
        "trouble in quarters. your foundation is shaking. deal with the basics first.",
        "the quarters rattle. routine breaks down. rebuild it gently.",
        "your quarters feel foreign today. even home has off days.",
        "trouble in the quarters. the structure needs patching before anything else.",
    ],
    "greenhouse": [
        "the greenhouse thorns are out. tread carefully around hearts today.",
        "trouble in the greenhouse. love is a minefield today.",
        "the greenhouse wilts. don't water dead things. focus on what's alive.",
        "the greenhouse air is thick. give feelings room to breathe.",
    ],
    "bridge": [
        "trouble on the bridge. every captain has bad days.",
        "the bridge shakes. emotions cloud the instruments.",
        "trouble on the bridge. your gut lies today. use your head instead.",
        "the bridge is stormy. feel it, but don't steer by it.",
    ],
}

# ────────────────────────────────────────────────────────────────
# Morning Briefing Templates — PRESSURE (8+ total)
# ────────────────────────────────────────────────────────────────

PRESSURE_TEMPLATES: Dict[str, List[str]] = {
    "greenhouse": [
        "pressure in the greenhouse. something is growing whether you want it to or not.",
        "the greenhouse pushes back. growth and discomfort share a root.",
    ],
    "bridge": [
        "the bridge demands a choice. both options are correct. pick one.",
        "pressure on the bridge. your emotions want two things at once.",
    ],
    "observatory": [
        "pressure in the observatory. the question has no clean answer. sit with it.",
        "the observatory pulls you in two directions. the truth is in the tension.",
    ],
    "workshop": [
        "pressure in the workshop. the thing you're building is reshaping you.",
        "the workshop demands more than you planned. rise to it or set it down.",
    ],
    "commons": [
        "pressure in the commons. someone needs you to choose a side.",
        "the commons buzz with expectation. not all of it is yours to carry.",
    ],
    "shrine": [
        "pressure in the shrine. who you are and who you're becoming are arguing.",
        "the shrine hums with intensity. transformation is not comfortable.",
    ],
    "quarters": [
        "pressure in the quarters. the old routine is cracking. that might be the point.",
        "the quarters shift beneath you. stability is being redefined.",
    ],
}

# Generic pressure templates (module-agnostic)
PRESSURE_GENERIC: List[str] = [
    "mercury is retrograde. nothing you start today will go as planned. maybe that's fine.",
    "the station creaks under cosmic pressure. you are the thing holding it together.",
    "tension everywhere. tension is just potential with nowhere to go yet.",
    "the stars are pulling in opposite directions. you are the fulcrum.",
]


# ────────────────────────────────────────────────────────────────
# Event Trigger Templates (25 total)
# ────────────────────────────────────────────────────────────────

EVENT_TEMPLATES: Dict[str, List[str]] = {
    "full_moon": [
        "full moon tonight. your station runs at 110%. don't overthink it.",
        "the moon is full. everything you've been building is illuminated now.",
        "full moon. the tides pull at your station. let them.",
    ],
    "new_moon": [
        "new moon. the sky is dark. perfect for secrets.",
        "new moon tonight. plant something in the dark. tend it later.",
        "the moon disappears. in the absence, you are your own light.",
    ],
    "meteor_shower": [
        "the perseids are peaking. the sky is literally falling for you.",
        "meteor shower tonight. the universe is throwing sparks.",
        "shooting stars. make a wish. the station is listening.",
    ],
    "mercury_retrograde": [
        "mercury stations retrograde today. buckle in.",
        "mercury goes backwards. your observatory instruments may lie.",
        "retrograde season. double-check everything. trust nothing digital.",
    ],
    "solar_flare": [
        "solar flare detected. your shields may flicker.",
        "solar storm incoming. the station's energy spikes unpredictably.",
    ],
    "asteroid_approach": [
        "an asteroid the size of a cathedral is passing earth right now. just thought you should know.",
        "near-earth asteroid today. the universe reminding you how small and lucky you are.",
    ],
    "iss_pass": [
        "the ISS is crossing your sky in 12 minutes. look up.",
        "the space station flies overhead tonight. wave at your neighbors.",
    ],
    "planet_conjunction": [
        "a planet conjunction tonight. alignment is not coincidence.",
        "two planets meet in the sky. when things align, pay attention.",
    ],
    "planet_opposition": [
        "jupiter is at opposition tonight. the biggest planet is closest. think big.",
        "opposition tonight. the sky holds a mirror up. look.",
    ],
    "eclipse": [
        "eclipse today. the light goes out so you can see what glows on its own.",
        "the shadow passes. eclipses end. what they reveal does not.",
    ],
    "zodiac_season": [
        "venus enters your sign today. beauty finds you whether you're ready or not.",
        "a new zodiac season begins. the energy shifts. shift with it.",
    ],
    "ar_session_complete": [
        "sky scanner session complete. you mapped {count} objects. the sky remembers.",
        "session ended. {count} identifications. the stars know your name now.",
    ],
    "ar_constellation_found": [
        "{name} identified. ancient sailors used the same pattern. you're in good company.",
        "you found {name}. it's been there for millennia. now it's yours.",
    ],
    "ar_iss_spotted": [
        "ISS spotted. six humans in a tin can, and you found them from below.",
        "you caught the space station. it crosses your sky in four minutes. blink and you'll miss it.",
    ],
}


# ────────────────────────────────────────────────────────────────
# Re-engagement Templates (12 total)
# ────────────────────────────────────────────────────────────────

RE_ENGAGEMENT_TEMPLATES: List[str] = [
    "your station is still here. the stars moved on. you should too.",
    "jupiter entered your 10th house while you were gone. your station's reputation precedes it.",
    "three sunrises without you. the observatory misses your curiosity.",
    "the crew kept things running. but they prefer your company.",
    "the cosmos doesn't pause. neither should you. come back when you're ready.",
    "your station is gathering stardust. literally. come collect it.",
    "the greenhouse grew something while you were away. come see.",
    "your station kept your seat warm. the bridge awaits.",
    "the stars rearranged while you were gone. the view is different now.",
    "your observatory recorded something interesting. come take a look.",
    "the workshop has a project half-finished. it's waiting for your hands.",
    "the station hums quietly without you. it hums louder when you return.",
]


# ────────────────────────────────────────────────────────────────
# Ad Reward Templates (TASK-017) — 8 total
# ────────────────────────────────────────────────────────────────

AD_REWARD_TEMPLATES: Dict[str, List[str]] = {
    "stardust_earned": [
        "stardust collected. the beacon dims. the cosmos pays its debts.",
        "a handful of stardust drifts through the airlock. it's yours now.",
        "the ad beacon pulses once and goes quiet. stardust settles on your console.",
    ],
    "freeze_granted": [
        "a streak freeze crystallizes in your quarters. use it when the cosmos demands a pause.",
        "the cold preservation unit hums. one freeze stored. your streak sleeps safely.",
    ],
    "xp_earned": [
        "season XP acquired. the pass advances. momentum is a kind of gravity.",
        "the station logs your progress. every signal watched moves the needle.",
    ],
    "daily_bonus": [
        "daily bonus collected. the station appreciates your attention. the stars notice consistency.",
    ],
}


# ────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────

MAX_DAILY_NOTIFICATIONS = 2
RE_ENGAGEMENT_MIN_DAYS = 3
RE_ENGAGEMENT_COOLDOWN_DAYS = 7
DEFAULT_QUIET_START = "22:00"
DEFAULT_QUIET_END = "08:00"
DEFAULT_BRIEFING_TIME = "08:00"
DEFAULT_TIMEZONE = "UTC"

# Module ID normalization
MODULE_NAMES_LOWER = [
    "observatory", "greenhouse", "workshop",
    "commons", "quarters", "bridge", "shrine",
]


# ────────────────────────────────────────────────────────────────
# Internal Helpers — Persistence
# ────────────────────────────────────────────────────────────────

def _sanitize_id(player_id: str) -> str:
    """Sanitize a player ID for filesystem use."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in player_id)


def _prefs_path(player_id: str) -> Path:
    """Return the file path for a player's notification preferences."""
    return PREFS_DIR / f"{_sanitize_id(player_id)}.json"


def _history_path(player_id: str) -> Path:
    """Return the file path for a player's notification history."""
    return HISTORY_DIR / f"{_sanitize_id(player_id)}.json"


def _ensure_prefs_dir() -> None:
    """Create the preferences directory if needed."""
    PREFS_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_history_dir() -> None:
    """Create the history directory if needed."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _prefs_to_dict(prefs: NotificationPreferences) -> dict:
    """Serialize preferences to a JSON-safe dictionary."""
    return {
        "player_id": prefs.player_id,
        "enabled": prefs.enabled,
        "morning_briefing": prefs.morning_briefing,
        "event_triggers": prefs.event_triggers,
        "re_engagement": prefs.re_engagement,
        "quiet_hours_start": prefs.quiet_hours_start,
        "quiet_hours_end": prefs.quiet_hours_end,
        "preferred_briefing_time": prefs.preferred_briefing_time,
        "timezone": prefs.timezone,
        "last_active": prefs.last_active,
    }


def _prefs_from_dict(data: dict) -> NotificationPreferences:
    """Deserialize preferences from a dictionary."""
    return NotificationPreferences(
        player_id=data["player_id"],
        enabled=data.get("enabled", True),
        morning_briefing=data.get("morning_briefing", True),
        event_triggers=data.get("event_triggers", True),
        re_engagement=data.get("re_engagement", True),
        quiet_hours_start=data.get("quiet_hours_start", DEFAULT_QUIET_START),
        quiet_hours_end=data.get("quiet_hours_end", DEFAULT_QUIET_END),
        preferred_briefing_time=data.get("preferred_briefing_time", DEFAULT_BRIEFING_TIME),
        timezone=data.get("timezone", DEFAULT_TIMEZONE),
        last_active=data.get("last_active", datetime.utcnow().isoformat()),
    )


def _payload_to_dict(payload: NotificationPayload) -> dict:
    """Serialize a notification payload to a dictionary."""
    return {
        "id": payload.id,
        "player_id": payload.player_id,
        "category": payload.category,
        "title": payload.title,
        "body": payload.body,
        "module_id": payload.module_id,
        "cosmic_status": payload.cosmic_status,
        "event_type": payload.event_type,
        "scheduled_time": payload.scheduled_time,
        "sent": payload.sent,
        "read": payload.read,
        "created_at": payload.created_at,
    }


def _payload_from_dict(data: dict) -> NotificationPayload:
    """Deserialize a notification payload from a dictionary."""
    return NotificationPayload(
        id=data["id"],
        player_id=data["player_id"],
        category=data["category"],
        title=data["title"],
        body=data["body"],
        module_id=data.get("module_id"),
        cosmic_status=data.get("cosmic_status"),
        event_type=data.get("event_type"),
        scheduled_time=data["scheduled_time"],
        sent=data.get("sent", False),
        read=data.get("read", False),
        created_at=data["created_at"],
    )


def _save_prefs(prefs: NotificationPreferences) -> None:
    """Write preferences to disk."""
    _ensure_prefs_dir()
    path = _prefs_path(prefs.player_id)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(_prefs_to_dict(prefs), fh, indent=2)
    except IOError:
        pass


def _load_history(player_id: str) -> NotificationHistory:
    """Load notification history from disk or create empty."""
    path = _history_path(player_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            notifications = [_payload_from_dict(n) for n in data.get("notifications", [])]
            daily_count = data.get("daily_count", {})
            return NotificationHistory(
                player_id=player_id,
                notifications=notifications,
                daily_count=daily_count,
            )
        except (json.JSONDecodeError, IOError, KeyError):
            pass
    return NotificationHistory(player_id=player_id, notifications=[], daily_count={})


def _save_history(history: NotificationHistory) -> None:
    """Write notification history to disk."""
    _ensure_history_dir()
    path = _history_path(history.player_id)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({
                "player_id": history.player_id,
                "notifications": [_payload_to_dict(n) for n in history.notifications],
                "daily_count": history.daily_count,
            }, fh, indent=2)
    except IOError:
        pass


def _record_notification(payload: NotificationPayload) -> None:
    """Record a sent notification in history and update daily count."""
    history = _load_history(payload.player_id)
    history.notifications.insert(0, payload)

    # Keep history to a reasonable size (last 200)
    if len(history.notifications) > 200:
        history.notifications = history.notifications[:200]

    # Update daily count
    today_str = date.today().isoformat()
    history.daily_count[today_str] = history.daily_count.get(today_str, 0) + 1

    _save_history(history)


# ────────────────────────────────────────────────────────────────
# Internal Helpers — Scheduling Rules
# ────────────────────────────────────────────────────────────────

def _is_quiet_hours(prefs: NotificationPreferences) -> bool:
    """Check if the current time falls within the player's quiet hours.

    Uses UTC comparison. In production, this would use the player's
    timezone for accurate local-time checking.
    """
    now = datetime.utcnow().time()
    try:
        start_parts = prefs.quiet_hours_start.split(":")
        end_parts = prefs.quiet_hours_end.split(":")
        quiet_start = time(int(start_parts[0]), int(start_parts[1]))
        quiet_end = time(int(end_parts[0]), int(end_parts[1]))
    except (ValueError, IndexError):
        return False

    # Handle overnight quiet hours (e.g. 22:00 - 08:00)
    if quiet_start > quiet_end:
        # Quiet if after start OR before end
        return now >= quiet_start or now < quiet_end
    else:
        # Quiet if between start and end
        return quiet_start <= now < quiet_end


def _get_daily_count_for_player(player_id: str, date_str: Optional[str] = None) -> int:
    """Get the number of notifications sent to a player today."""
    if date_str is None:
        date_str = date.today().isoformat()
    history = _load_history(player_id)
    return history.daily_count.get(date_str, 0)


def _get_last_re_engagement_date(player_id: str) -> Optional[str]:
    """Get the date of the last re-engagement notification sent."""
    history = _load_history(player_id)
    for notif in history.notifications:
        if notif.category == "re_engagement":
            return notif.created_at[:10]  # Extract date portion
    return None


def _deterministic_pick(templates: List[str], seed_str: str) -> str:
    """Pick a template deterministically based on a seed string.

    Uses MD5 hash of the seed for repeatable but varied selection.
    """
    seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    return templates[seed % len(templates)]


# ────────────────────────────────────────────────────────────────
# Public API — Preference Management
# ────────────────────────────────────────────────────────────────

def get_preferences(player_id: str) -> NotificationPreferences:
    """Load notification preferences from disk or create defaults.

    Args:
        player_id: Unique player identifier.

    Returns:
        NotificationPreferences for this player.
    """
    path = _prefs_path(player_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return _prefs_from_dict(data)
        except (json.JSONDecodeError, IOError, KeyError):
            pass

    # Create defaults
    prefs = NotificationPreferences(
        player_id=player_id,
        enabled=True,
        morning_briefing=True,
        event_triggers=True,
        re_engagement=True,
        quiet_hours_start=DEFAULT_QUIET_START,
        quiet_hours_end=DEFAULT_QUIET_END,
        preferred_briefing_time=DEFAULT_BRIEFING_TIME,
        timezone=DEFAULT_TIMEZONE,
        last_active=datetime.utcnow().isoformat(),
    )
    _save_prefs(prefs)
    return prefs


def update_preferences(player_id: str, updates: dict) -> NotificationPreferences:
    """Update specific notification preference fields.

    Args:
        player_id: Unique player identifier.
        updates:   Dictionary of fields to update. Valid keys:
                   enabled, morning_briefing, event_triggers,
                   re_engagement, quiet_hours_start, quiet_hours_end,
                   preferred_briefing_time, timezone, last_active.

    Returns:
        Updated NotificationPreferences.
    """
    prefs = get_preferences(player_id)

    valid_fields = {
        "enabled", "morning_briefing", "event_triggers", "re_engagement",
        "quiet_hours_start", "quiet_hours_end", "preferred_briefing_time",
        "timezone", "last_active",
    }

    for key, value in updates.items():
        if key in valid_fields:
            setattr(prefs, key, value)

    _save_prefs(prefs)
    return prefs


def record_app_open(player_id: str) -> None:
    """Record that the player opened the app (updates last_active).

    Args:
        player_id: Unique player identifier.
    """
    update_preferences(player_id, {"last_active": datetime.utcnow().isoformat()})


# ────────────────────────────────────────────────────────────────
# Public API — Rule Checking
# ────────────────────────────────────────────────────────────────

def can_send_notification(
    player_id: str,
    category: str,
) -> Tuple[bool, str]:
    """Check whether a notification can be sent to this player.

    Evaluates all scheduling rules:
        1. Master toggle enabled
        2. Category-specific toggle enabled
        3. Daily limit not exceeded (max 2/day)
        4. Not during quiet hours
        5. Re-engagement cooldown (3+ days away, max 1x/week)

    Args:
        player_id: Unique player identifier.
        category:  One of "morning_briefing", "event_trigger", "re_engagement".

    Returns:
        Tuple of (allowed: bool, reason: str).
    """
    prefs = get_preferences(player_id)

    # Rule 1: Master toggle
    if not prefs.enabled:
        return False, "notifications disabled by player"

    # Rule 2: Category toggle
    category_map = {
        "morning_briefing": prefs.morning_briefing,
        "event_trigger": prefs.event_triggers,
        "re_engagement": prefs.re_engagement,
    }
    if not category_map.get(category, False):
        return False, f"{category} notifications disabled by player"

    # Rule 3: Daily limit
    daily_count = _get_daily_count_for_player(player_id)
    if daily_count >= MAX_DAILY_NOTIFICATIONS:
        return False, f"daily limit reached ({MAX_DAILY_NOTIFICATIONS} notifications sent today)"

    # Rule 4: Quiet hours
    if _is_quiet_hours(prefs):
        return False, "quiet hours active"

    # Rule 5: Re-engagement specific rules
    if category == "re_engagement":
        # Check days since last active
        try:
            last_active_dt = datetime.fromisoformat(prefs.last_active)
            days_away = (datetime.utcnow() - last_active_dt).days
            if days_away < RE_ENGAGEMENT_MIN_DAYS:
                return False, f"player active within {RE_ENGAGEMENT_MIN_DAYS} days (last active {days_away} days ago)"
        except (ValueError, TypeError):
            pass

        # Check cooldown since last re-engagement
        last_re = _get_last_re_engagement_date(player_id)
        if last_re:
            try:
                last_re_date = date.fromisoformat(last_re)
                days_since = (date.today() - last_re_date).days
                if days_since < RE_ENGAGEMENT_COOLDOWN_DAYS:
                    return False, f"re-engagement cooldown ({days_since}/{RE_ENGAGEMENT_COOLDOWN_DAYS} days)"
            except (ValueError, TypeError):
                pass

    return True, "all checks passed"


# ────────────────────────────────────────────────────────────────
# Public API — Notification Generators
# ────────────────────────────────────────────────────────────────

def generate_morning_briefing(
    player_id: str,
    module_statuses: List[dict],
    date_str: Optional[str] = None,
) -> NotificationPayload:
    """Generate a personalized morning briefing notification.

    Selects a template based on the strongest cosmic status among
    the player's modules. Voice: lowercase, poetic, blunt.

    Args:
        player_id:       Unique player identifier.
        module_statuses: List of dicts with keys:
                         - module_id (str): e.g. "observatory"
                         - cosmic_status (str): "POWER", "TROUBLE", "PRESSURE"
                         - buff_percentage (int): signed buff value
        date_str:        Optional ISO date string. Defaults to today.

    Returns:
        A NotificationPayload ready for delivery.
    """
    if date_str is None:
        date_str = date.today().isoformat()

    now_iso = datetime.utcnow().isoformat()

    # Find the strongest status (highest absolute buff_percentage)
    strongest_module = None
    strongest_status = None
    strongest_buff = 0

    for ms in module_statuses:
        module_id = ms.get("module_id", "").lower()
        status = ms.get("cosmic_status", "NEUTRAL")
        buff = abs(ms.get("buff_percentage", 0))

        if status in ("POWER", "TROUBLE", "PRESSURE") and buff >= strongest_buff:
            strongest_module = module_id
            strongest_status = status
            strongest_buff = buff

    # Select template based on status
    body = ""
    selected_module = strongest_module

    if strongest_status == "POWER" and strongest_module in POWER_TEMPLATES:
        templates = POWER_TEMPLATES[strongest_module]
        body = _deterministic_pick(templates, f"{date_str}:{player_id}:power")
    elif strongest_status == "TROUBLE" and strongest_module in TROUBLE_TEMPLATES:
        templates = TROUBLE_TEMPLATES[strongest_module]
        body = _deterministic_pick(templates, f"{date_str}:{player_id}:trouble")
    elif strongest_status == "PRESSURE":
        if strongest_module in PRESSURE_TEMPLATES:
            templates = PRESSURE_TEMPLATES[strongest_module]
            body = _deterministic_pick(templates, f"{date_str}:{player_id}:pressure")
        else:
            body = _deterministic_pick(PRESSURE_GENERIC, f"{date_str}:{player_id}:pressure")
    else:
        # Fallback: no strong status, pick a generic power message
        all_power = []
        for templates in POWER_TEMPLATES.values():
            all_power.extend(templates)
        body = _deterministic_pick(all_power, f"{date_str}:{player_id}:neutral")
        selected_module = None
        strongest_status = None

    payload = NotificationPayload(
        id=str(uuid.uuid4()),
        player_id=player_id,
        category="morning_briefing",
        title="cosmic briefing",
        body=body,
        module_id=selected_module,
        cosmic_status=strongest_status,
        event_type=None,
        scheduled_time=now_iso,
        sent=True,
        read=False,
        created_at=now_iso,
    )

    _record_notification(payload)
    return payload


def generate_event_notification(
    player_id: str,
    event_type: str,
    event_data: Optional[dict] = None,
) -> Optional[NotificationPayload]:
    """Generate an event-triggered notification.

    Checks daily limit (max 1 event per day if briefing already sent)
    and quiet hours before generating.

    Args:
        player_id:  Unique player identifier.
        event_type: One of: "full_moon", "new_moon", "meteor_shower",
                    "mercury_retrograde", "solar_flare", "asteroid_approach",
                    "iss_pass", "planet_conjunction", "planet_opposition",
                    "eclipse", "zodiac_season".
        event_data: Optional dict with additional event context.

    Returns:
        A NotificationPayload if allowed, or None if blocked by rules.
    """
    # Check rules
    allowed, reason = can_send_notification(player_id, "event_trigger")
    if not allowed:
        return None

    # Get templates for this event type
    templates = EVENT_TEMPLATES.get(event_type)
    if not templates:
        return None

    now_iso = datetime.utcnow().isoformat()
    today_str = date.today().isoformat()

    body = _deterministic_pick(templates, f"{today_str}:{player_id}:{event_type}")

    payload = NotificationPayload(
        id=str(uuid.uuid4()),
        player_id=player_id,
        category="event_trigger",
        title="cosmic event",
        body=body,
        module_id=None,
        cosmic_status=None,
        event_type=event_type,
        scheduled_time=now_iso,
        sent=True,
        read=False,
        created_at=now_iso,
    )

    _record_notification(payload)
    return payload


def generate_re_engagement(
    player_id: str,
) -> Optional[NotificationPayload]:
    """Generate a re-engagement notification.

    Only sends if player has been away 3+ days and no re-engagement
    was sent in the past 7 days. Never guilt-trips.

    Args:
        player_id: Unique player identifier.

    Returns:
        A NotificationPayload if conditions are met, or None.
    """
    # Check all rules
    allowed, reason = can_send_notification(player_id, "re_engagement")
    if not allowed:
        return None

    now_iso = datetime.utcnow().isoformat()
    today_str = date.today().isoformat()

    body = _deterministic_pick(RE_ENGAGEMENT_TEMPLATES, f"{today_str}:{player_id}:re_engage")

    payload = NotificationPayload(
        id=str(uuid.uuid4()),
        player_id=player_id,
        category="re_engagement",
        title="station update",
        body=body,
        module_id=None,
        cosmic_status=None,
        event_type=None,
        scheduled_time=now_iso,
        sent=True,
        read=False,
        created_at=now_iso,
    )

    _record_notification(payload)
    return payload


# ────────────────────────────────────────────────────────────────
# Public API — History & Tracking
# ────────────────────────────────────────────────────────────────

def get_notification_history(
    player_id: str,
    limit: int = 20,
) -> List[NotificationPayload]:
    """Retrieve notification history for a player.

    Args:
        player_id: Unique player identifier.
        limit:     Maximum number of notifications to return.

    Returns:
        List of NotificationPayload, most recent first.
    """
    history = _load_history(player_id)
    return history.notifications[:limit]


def mark_notification_read(
    player_id: str,
    notification_id: str,
) -> bool:
    """Mark a notification as read.

    Args:
        player_id:       Unique player identifier.
        notification_id: UUID of the notification.

    Returns:
        True if the notification was found and marked, False otherwise.
    """
    history = _load_history(player_id)
    for notif in history.notifications:
        if notif.id == notification_id:
            notif.read = True
            _save_history(history)
            return True
    return False


def get_daily_count(
    player_id: str,
    date_str: Optional[str] = None,
) -> int:
    """Get the number of notifications sent to a player on a given date.

    Args:
        player_id: Unique player identifier.
        date_str:  ISO date string (YYYY-MM-DD). Defaults to today.

    Returns:
        Count of notifications sent on that date.
    """
    return _get_daily_count_for_player(player_id, date_str)


# ────────────────────────────────────────────────────────────────
# Serialization Helpers (for API responses)
# ────────────────────────────────────────────────────────────────

def notification_to_dict(payload: NotificationPayload) -> dict:
    """Serialize a NotificationPayload to a JSON-safe dictionary."""
    return _payload_to_dict(payload)


def preferences_to_dict(prefs: NotificationPreferences) -> dict:
    """Serialize NotificationPreferences to a JSON-safe dictionary."""
    return _prefs_to_dict(prefs)

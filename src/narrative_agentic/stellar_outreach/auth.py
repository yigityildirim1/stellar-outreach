"""
NEXUS STATION — Player Authentication & Registration

Single-player identity persistence via UUID.
No passwords, no JWT, no sessions.
Birth data is PII — stored only on-device, never persisted server-side.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Storage directory for player records
_AUTH_DIR = Path.home() / ".nexus_station" / "auth"


def _ensure_dir():
    _AUTH_DIR.mkdir(parents=True, exist_ok=True)


def register_player() -> dict:
    """Generate a new player UUID and create a minimal record on disk."""
    _ensure_dir()
    player_id = str(uuid.uuid4())
    record = {
        "player_id": player_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "onboarded": False,
    }
    path = _AUTH_DIR / f"{player_id}.json"
    with open(path, "w") as f:
        json.dump(record, f, indent=2)
    return record


def complete_onboarding(player_id: str) -> dict:
    """Mark a player as fully onboarded."""
    path = _AUTH_DIR / f"{player_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Player {player_id} not found")
    with open(path) as f:
        record = json.load(f)
    record["onboarded"] = True
    record["onboarded_at"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w") as f:
        json.dump(record, f, indent=2)
    return record


def check_player(player_id: str) -> dict:
    """Check if a player exists and return their record."""
    path = _AUTH_DIR / f"{player_id}.json"
    if not path.exists():
        return {"exists": False, "player_id": player_id}
    with open(path) as f:
        record = json.load(f)
    return {"exists": True, **record}

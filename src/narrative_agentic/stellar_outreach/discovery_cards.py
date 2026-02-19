"""
NEXUS STATION - Stellar Outreach: Discovery Cards (TASK-007)

NASA APOD Integration for daily Discovery Cards.
Fetches Astronomy Picture of the Day, enriches with space facts,
and manages player card collections.

GDD Reference: Section 11.2 - Discovery Card System
"""

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"
DEFAULT_API_KEY = "DEMO_KEY"
CACHE_DIR = Path.home() / ".nexus_station" / "apod_cache"
COLLECTION_DIR = Path.home() / ".nexus_station" / "card_collections"
REQUEST_TIMEOUT = 15  # seconds


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------

@dataclass
class DiscoveryCard:
    """A single Discovery Card generated from NASA APOD data."""

    id: str                     # e.g. "CARD-2026-02-10"
    date: str                   # ISO date string
    title: str                  # APOD title
    explanation: str            # APOD explanation text
    image_url: str              # HD image URL preferred
    media_type: str             # "image" or "video"
    did_you_know: str           # Rotating fun fact
    scale_comparison: str       # Scale comparison fact
    today_in_history: str       # Space history for this date
    collected: bool = False     # Whether player collected this card
    collection_month: str = ""  # e.g. "2026-02"

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DiscoveryCard":
        """Deserialize from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CardCollection:
    """Tracks a player's collected Discovery Cards."""

    player_id: str
    cards: dict[str, bool] = field(default_factory=dict)   # card_id -> collected
    months: dict[str, list[str]] = field(default_factory=dict)  # "2026-02" -> [card_ids]

    def add_card(self, card: DiscoveryCard) -> bool:
        """Mark a card as collected. Returns True if newly collected."""
        if self.cards.get(card.id):
            return False
        self.cards[card.id] = True
        month_key = card.collection_month or card.date[:7]
        if month_key not in self.months:
            self.months[month_key] = []
        if card.id not in self.months[month_key]:
            self.months[month_key].append(card.id)
        return True

    def is_month_complete(self, year: int, month: int) -> bool:
        """Check if every day in the given month has a collected card."""
        month_key = f"{year:04d}-{month:02d}"
        if month_key not in self.months:
            return False

        import calendar
        days_in_month = calendar.monthrange(year, month)[1]
        collected_ids = set(self.months[month_key])

        for day in range(1, days_in_month + 1):
            card_id = f"CARD-{year:04d}-{month:02d}-{day:02d}"
            if card_id not in collected_ids:
                return False
        return True

    def get_stats(self) -> dict:
        """Return collection statistics."""
        total = sum(1 for v in self.cards.values() if v)
        months_completed = []
        for month_key in self.months:
            parts = month_key.split("-")
            if len(parts) == 2:
                try:
                    if self.is_month_complete(int(parts[0]), int(parts[1])):
                        months_completed.append(month_key)
                except (ValueError, IndexError):
                    pass
        return {
            "player_id": self.player_id,
            "total_collected": total,
            "months_started": len(self.months),
            "months_completed": months_completed,
            "months_completed_count": len(months_completed),
        }

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CardCollection":
        return cls(
            player_id=data.get("player_id", "unknown"),
            cards=data.get("cards", {}),
            months=data.get("months", {}),
        )


# ---------------------------------------------------------------------------
# Space History Database (30+ entries)
# ---------------------------------------------------------------------------

SPACE_HISTORY: dict[str, str] = {
    "01-01": "On this day in 2019, NASA's New Horizons flew past Ultima Thule, the most distant object ever visited by a spacecraft.",
    "01-28": "On this day in 1986, the Space Shuttle Challenger broke apart 73 seconds after launch, claiming seven crew members.",
    "02-01": "On this day in 2003, the Space Shuttle Columbia disintegrated during re-entry, losing all seven crew members.",
    "02-18": "On this day in 1930, Clyde Tombaugh discovered Pluto at Lowell Observatory.",
    "02-20": "On this day in 1962, John Glenn became the first American to orbit the Earth aboard Friendship 7.",
    "03-14": "On this day in 2879 BCE... just kidding. Happy Pi Day! Pi is essential for calculating orbits and trajectories.",
    "03-18": "On this day in 1965, Alexei Leonov performed the first spacewalk, floating outside Voskhod 2 for 12 minutes.",
    "04-01": "On this day in 2006, ESA's Venus Express entered orbit around Venus to study its hostile atmosphere.",
    "04-12": "On this day in 1961, Yuri Gagarin became the first human in space aboard Vostok 1. Also in 1981, the first Space Shuttle Columbia launched.",
    "04-24": "On this day in 1990, the Hubble Space Telescope was launched aboard Space Shuttle Discovery.",
    "05-05": "On this day in 1961, Alan Shepard became the first American in space on a 15-minute suborbital flight.",
    "05-25": "On this day in 1961, President Kennedy announced the goal of landing a man on the Moon before the decade's end.",
    "06-16": "On this day in 1963, Valentina Tereshkova became the first woman in space aboard Vostok 6.",
    "06-18": "On this day in 1983, Sally Ride became the first American woman in space aboard Space Shuttle Challenger.",
    "07-04": "On this day in 1997, NASA's Mars Pathfinder landed on Mars and deployed the Sojourner rover.",
    "07-14": "On this day in 2015, NASA's New Horizons made its closest approach to Pluto, revealing a heart-shaped plain.",
    "07-20": "On this day in 1969, Neil Armstrong and Buzz Aldrin became the first humans to walk on the Moon during Apollo 11.",
    "08-06": "On this day in 2012, NASA's Curiosity rover landed on Mars using the sky crane maneuver.",
    "08-20": "On this day in 1977, Voyager 2 launched on its Grand Tour of the outer planets.",
    "08-25": "On this day in 2012, Voyager 1 crossed into interstellar space, the first human-made object to do so.",
    "09-05": "On this day in 1977, Voyager 1 launched, now the most distant human-made object at over 15 billion miles away.",
    "09-12": "On this day in 1992, Mae Jemison became the first African-American woman in space aboard Space Shuttle Endeavour.",
    "10-01": "On this day in 1958, NASA was officially established, replacing NACA.",
    "10-04": "On this day in 1957, the Soviet Union launched Sputnik 1, the first artificial satellite, starting the Space Age.",
    "10-14": "On this day in 2012, Felix Baumgartner completed a freefall from 128,100 feet, breaking the sound barrier.",
    "11-02": "On this day in 2000, the first crew arrived at the International Space Station, beginning continuous habitation.",
    "11-03": "On this day in 1957, the Soviet Union launched Sputnik 2 carrying Laika, the first animal to orbit Earth.",
    "11-20": "On this day in 1998, the first module of the International Space Station, Zarya, was launched.",
    "12-14": "On this day in 1972, Eugene Cernan became the last human to walk on the Moon during Apollo 17.",
    "12-21": "On this day in 1968, Apollo 8 launched, becoming the first crewed mission to orbit the Moon.",
    "12-24": "On this day in 1968, Apollo 8 astronauts took the iconic 'Earthrise' photo from lunar orbit.",
    "12-25": "On this day in 2021, the James Webb Space Telescope launched from French Guiana on an Ariane 5 rocket.",
}


# ---------------------------------------------------------------------------
# Did You Know? Facts (20+ entries)
# ---------------------------------------------------------------------------

DID_YOU_KNOW_FACTS: list[str] = [
    "A day on Venus is longer than its year. Venus takes 243 Earth days to rotate but only 225 to orbit the Sun.",
    "Neutron stars are so dense that a teaspoon of their material would weigh about 6 billion tons.",
    "There are more stars in the universe than grains of sand on all of Earth's beaches.",
    "The footprints on the Moon will likely remain for at least 100 million years since there is no wind to erode them.",
    "Space is completely silent because there is no atmosphere for sound waves to travel through.",
    "The largest known star, UY Scuti, could fit nearly 5 billion Suns inside it.",
    "A full NASA spacesuit costs approximately $12 million, with the backpack and life support adding another $10 million.",
    "The International Space Station travels at about 17,500 mph, orbiting Earth roughly every 90 minutes.",
    "Saturn would float in water if you could find a bathtub big enough, because its density is less than water.",
    "There is a giant cloud of alcohol in space (Sagittarius B2) spanning 288 billion miles.",
    "The Voyager 1 spacecraft is still sending data from over 15 billion miles away using a 23-watt transmitter.",
    "Jupiter's Great Red Spot is a storm that has been raging for at least 350 years.",
    "One million Earths could fit inside the Sun, which accounts for 99.86% of the Solar System's mass.",
    "The Andromeda Galaxy is on a collision course with the Milky Way, arriving in about 4.5 billion years.",
    "Light from the Sun takes about 8 minutes and 20 seconds to reach Earth.",
    "Olympus Mons on Mars is the tallest volcano in the solar system at nearly 72,000 feet (22 km) high.",
    "A year on Mercury is just 88 Earth days, but a single day (sunrise to sunrise) lasts 176 Earth days.",
    "The observable universe is about 93 billion light-years in diameter.",
    "If two pieces of the same metal touch in the vacuum of space, they will permanently bond together (cold welding).",
    "Astronauts grow up to 2 inches taller in space because the lack of gravity lets their spines expand.",
    "The Apollo astronauts' urine is still in bags on the Moon.",
    "There are more trees on Earth than stars in the Milky Way: roughly 3 trillion trees vs 100-400 billion stars.",
    "GPS satellites must account for both special and general relativity or they would drift by about 10 km per day.",
]


# ---------------------------------------------------------------------------
# Scale Comparisons (15+ entries)
# ---------------------------------------------------------------------------

SCALE_COMPARISONS: list[str] = [
    "The Sun could fit 1.3 million Earths inside it.",
    "Light from the nearest star, Proxima Centauri, takes 4.24 years to reach us.",
    "If the Sun were a front door, Earth would be a nickel 50 feet away.",
    "The Milky Way is so large that even at light speed, crossing it would take 100,000 years.",
    "The Voyager 1 probe, traveling at 38,000 mph, would take about 73,000 years to reach the nearest star.",
    "Jupiter is so massive that all the other planets could fit inside it combined.",
    "The distance from Earth to the Moon could fit all the other planets side by side.",
    "The Olympus Mons volcano on Mars is about the size of the entire state of Arizona.",
    "A neutron star the size of a sugar cube would weigh as much as all of humanity combined.",
    "The Bootes Void is a region of space so empty that it spans 330 million light-years with almost no galaxies.",
    "The Sun loses about 4 million tons of mass every second through nuclear fusion.",
    "If you could drive to the Sun at 60 mph, it would take about 176 years.",
    "The Orion Nebula is about 1,300 times the Sun-to-Pluto distance across.",
    "The cosmic microwave background radiation has traveled for 13.8 billion years to reach your TV antenna.",
    "One light-year is about 5.88 trillion miles. The observable universe is 93 billion light-years across.",
    "The Great Wall of galaxies stretches over 500 million light-years, one of the largest known structures in the universe.",
]


# ---------------------------------------------------------------------------
# Cache Utilities
# ---------------------------------------------------------------------------

def _ensure_cache_dir() -> None:
    """Create the cache directory if it does not exist."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(date_str: str) -> Path:
    """Return the cache file path for a given date."""
    return CACHE_DIR / f"{date_str}.json"


def _read_cache(date_str: str) -> Optional[dict]:
    """Read cached APOD data for the given date. Returns None on miss."""
    path = _cache_path(date_str)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def _write_cache(date_str: str, data: dict) -> None:
    """Write APOD data to the file cache."""
    _ensure_cache_dir()
    path = _cache_path(date_str)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except IOError:
        pass  # Graceful degradation: cache write failure is non-fatal


# ---------------------------------------------------------------------------
# Collection Persistence
# ---------------------------------------------------------------------------

def _ensure_collection_dir() -> None:
    COLLECTION_DIR.mkdir(parents=True, exist_ok=True)


def _collection_path(player_id: str) -> Path:
    # Sanitize player_id for filesystem safety
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in player_id)
    return COLLECTION_DIR / f"{safe_id}.json"


def _load_collection(player_id: str) -> CardCollection:
    path = _collection_path(player_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return CardCollection.from_dict(json.load(fh))
        except (json.JSONDecodeError, IOError):
            pass
    return CardCollection(player_id=player_id)


def _save_collection(collection: CardCollection) -> None:
    _ensure_collection_dir()
    path = _collection_path(collection.player_id)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(collection.to_dict(), fh, indent=2)
    except IOError:
        pass


# ---------------------------------------------------------------------------
# Enrichment Helpers
# ---------------------------------------------------------------------------

def _get_today_in_history(date_str: str) -> str:
    """Return a space history fact for the given date, or a generic one."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        key = dt.strftime("%m-%d")
    except ValueError:
        key = ""

    if key in SPACE_HISTORY:
        return SPACE_HISTORY[key]
    return "No specific space history event recorded for this date. Every day is a good day for discovery!"


def _get_did_you_know(date_str: str) -> str:
    """Return a deterministic fun fact based on the date."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_of_year = dt.timetuple().tm_yday
    except ValueError:
        day_of_year = 0
    index = day_of_year % len(DID_YOU_KNOW_FACTS)
    return DID_YOU_KNOW_FACTS[index]


def _get_scale_comparison(date_str: str) -> str:
    """Return a deterministic scale comparison based on the date."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_of_year = dt.timetuple().tm_yday
    except ValueError:
        day_of_year = 0
    index = day_of_year % len(SCALE_COMPARISONS)
    return SCALE_COMPARISONS[index]


# ---------------------------------------------------------------------------
# Fallback Card
# ---------------------------------------------------------------------------

def _fallback_card(date_str: str) -> dict:
    """Return a fallback APOD-like payload when the API is unavailable."""
    return {
        "date": date_str,
        "title": "The Cosmos Awaits",
        "explanation": (
            "Unable to reach the NASA APOD service at this time. "
            "The universe is vast and sometimes our connection to Earth's "
            "servers is briefly interrupted. Check back soon for today's "
            "Astronomy Picture of the Day."
        ),
        "url": "",
        "hdurl": "",
        "media_type": "image",
    }


# ---------------------------------------------------------------------------
# NASA APOD Fetcher
# ---------------------------------------------------------------------------

def _fetch_apod(date_str: str, api_key: Optional[str] = None) -> dict:
    """
    Fetch NASA APOD data for the given date.

    Checks cache first. On cache miss, calls the NASA API.
    Falls back to a placeholder if the API is unreachable.
    """
    # Check cache
    cached = _read_cache(date_str)
    if cached is not None:
        return cached

    # Build request URL
    key = api_key or os.environ.get("NASA_API_KEY", DEFAULT_API_KEY)
    url = f"{NASA_APOD_URL}?api_key={key}&date={date_str}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-Station/1.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _write_cache(date_str, data)
            return data
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError):
        # Graceful degradation: return fallback
        return _fallback_card(date_str)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_daily_card(date_str: Optional[str] = None, api_key: Optional[str] = None) -> DiscoveryCard:
    """
    Fetch (or retrieve from cache) the Discovery Card for a given date.

    Parameters
    ----------
    date_str : str, optional
        ISO date (YYYY-MM-DD). Defaults to today.
    api_key : str, optional
        NASA API key. Defaults to DEMO_KEY.

    Returns
    -------
    DiscoveryCard
        Fully enriched discovery card.
    """
    if date_str is None:
        date_str = date.today().isoformat()

    apod = _fetch_apod(date_str, api_key)

    card_id = f"CARD-{date_str}"
    image_url = apod.get("hdurl") or apod.get("url", "")
    collection_month = date_str[:7] if len(date_str) >= 7 else ""

    return DiscoveryCard(
        id=card_id,
        date=date_str,
        title=apod.get("title", "Unknown"),
        explanation=apod.get("explanation", ""),
        image_url=image_url,
        media_type=apod.get("media_type", "image"),
        did_you_know=_get_did_you_know(date_str),
        scale_comparison=_get_scale_comparison(date_str),
        today_in_history=_get_today_in_history(date_str),
        collected=False,
        collection_month=collection_month,
    )


def get_card_collection(player_id: str) -> CardCollection:
    """Load a player's card collection from disk."""
    return _load_collection(player_id)


def collect_card(player_id: str, card_id: str, date_str: Optional[str] = None) -> bool:
    """
    Add a card to a player's collection.

    Parameters
    ----------
    player_id : str
        The player identifier.
    card_id : str
        The card ID to collect (e.g. "CARD-2026-02-10").
    date_str : str, optional
        The date of the card. Extracted from card_id if not provided.

    Returns
    -------
    bool
        True if the card was newly collected, False if already owned.
    """
    if date_str is None:
        # Extract date from card_id: "CARD-2026-02-10" -> "2026-02-10"
        date_str = card_id.replace("CARD-", "", 1) if card_id.startswith("CARD-") else date.today().isoformat()

    collection = _load_collection(player_id)

    card = DiscoveryCard(
        id=card_id,
        date=date_str,
        title="",
        explanation="",
        image_url="",
        media_type="image",
        did_you_know="",
        scale_comparison="",
        today_in_history="",
        collected=True,
        collection_month=date_str[:7] if len(date_str) >= 7 else "",
    )

    newly_collected = collection.add_card(card)
    if newly_collected:
        _save_collection(collection)
    return newly_collected

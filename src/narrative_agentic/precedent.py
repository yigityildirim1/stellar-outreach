"""
Precedent module - Institutional memory and decision tracking.

"Every decision must cite precedent or establish new precedent."
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum
import hashlib
import json


class PrecedentType(Enum):
    """Types of precedents."""
    POLICY = "policy"  # General policy decisions
    TECHNICAL = "technical"  # Technical implementation decisions
    ETHICAL = "ethical"  # Ethics-related decisions
    SECURITY = "security"  # Security-related decisions
    DESIGN = "design"  # Design/UX decisions
    PROCESS = "process"  # Process/workflow decisions
    EXCEPTION = "exception"  # Exceptions to normal rules
    CUSTOM = "custom"


class PrecedentStatus(Enum):
    """Status of a precedent."""
    ACTIVE = "active"  # Currently in effect
    SUPERSEDED = "superseded"  # Replaced by newer precedent
    DEPRECATED = "deprecated"  # No longer recommended
    ARCHIVED = "archived"  # Historical reference only


@dataclass
class Precedent:
    """
    A precedent - a recorded decision that informs future decisions.

    Precedents are the building blocks of institutional memory.
    They capture not just what was decided, but why.
    """

    id: str
    title: str
    description: str
    rationale: str
    precedent_type: PrecedentType = PrecedentType.CUSTOM
    status: PrecedentStatus = PrecedentStatus.ACTIVE

    # Context
    loop_number: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""

    # References
    cited_precedents: list[str] = field(default_factory=list)  # IDs of precedents this cites
    supersedes: Optional[str] = None  # ID of precedent this supersedes
    tags: list[str] = field(default_factory=list)

    # Consultation
    crew_consulted: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            # Generate ID from title and timestamp
            content = f"{self.title}{self.created_at.isoformat()}"
            self.id = hashlib.sha256(content.encode()).hexdigest()[:12]

    def cite(self) -> str:
        """Return a citation string for this precedent."""
        return f"[PRECEDENT-{self.id}] {self.title}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "type": self.precedent_type.value,
            "status": self.status.value,
            "loop": self.loop_number,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "cited": self.cited_precedents,
            "supersedes": self.supersedes,
            "tags": self.tags,
            "crew_consulted": self.crew_consulted,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Precedent":
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            rationale=data["rationale"],
            precedent_type=PrecedentType(data.get("type", "custom")),
            status=PrecedentStatus(data.get("status", "active")),
            loop_number=data.get("loop", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            created_by=data.get("created_by", ""),
            cited_precedents=data.get("cited", []),
            supersedes=data.get("supersedes"),
            tags=data.get("tags", []),
            crew_consulted=data.get("crew_consulted", []),
        )

    def __str__(self) -> str:
        lines = [
            f"PRECEDENT-{self.id}: {self.title}",
            f"Type: {self.precedent_type.value} | Status: {self.status.value}",
            f"",
            f"Description: {self.description}",
            f"",
            f"Rationale: {self.rationale}",
        ]

        if self.cited_precedents:
            lines.append(f"Cites: {', '.join(self.cited_precedents)}")

        if self.crew_consulted:
            lines.append(f"Consulted: {', '.join(self.crew_consulted)}")

        return "\n".join(lines)


class PrecedentLog:
    """
    The precedent log - institutional memory for a Narrative Agentic system.

    This maintains the history of all decisions and their rationale,
    allowing future decisions to cite or build upon past decisions.
    """

    def __init__(self):
        self.precedents: dict[str, Precedent] = {}
        self._by_type: dict[PrecedentType, list[str]] = {t: [] for t in PrecedentType}
        self._by_tag: dict[str, list[str]] = {}

    def establish(
        self,
        title: str,
        description: str,
        rationale: str,
        precedent_type: PrecedentType = PrecedentType.CUSTOM,
        loop_number: int = 0,
        created_by: str = "",
        cited_precedents: list[str] = None,
        supersedes: str = None,
        tags: list[str] = None,
        crew_consulted: list[str] = None,
    ) -> Precedent:
        """
        Establish a new precedent.

        This is the primary way to record decisions in the institutional memory.
        """
        precedent = Precedent(
            id="",  # Will be auto-generated
            title=title,
            description=description,
            rationale=rationale,
            precedent_type=precedent_type,
            loop_number=loop_number,
            created_by=created_by,
            cited_precedents=cited_precedents or [],
            supersedes=supersedes,
            tags=tags or [],
            crew_consulted=crew_consulted or [],
        )

        # If superseding another precedent, mark it
        if supersedes and supersedes in self.precedents:
            self.precedents[supersedes].status = PrecedentStatus.SUPERSEDED

        # Store the precedent
        self.precedents[precedent.id] = precedent
        self._by_type[precedent_type].append(precedent.id)

        for tag in precedent.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = []
            self._by_tag[tag].append(precedent.id)

        return precedent

    def get(self, precedent_id: str) -> Optional[Precedent]:
        """Get a precedent by ID."""
        return self.precedents.get(precedent_id)

    def cite(self, precedent_id: str) -> Optional[str]:
        """Get a citation for a precedent."""
        precedent = self.get(precedent_id)
        if precedent:
            return precedent.cite()
        return None

    def search(
        self,
        query: str = "",
        precedent_type: Optional[PrecedentType] = None,
        tags: list[str] = None,
        status: PrecedentStatus = PrecedentStatus.ACTIVE,
    ) -> list[Precedent]:
        """
        Search for relevant precedents.

        This is used when looking for precedents to cite.
        """
        results = []

        for precedent in self.precedents.values():
            # Filter by status
            if precedent.status != status:
                continue

            # Filter by type
            if precedent_type and precedent.precedent_type != precedent_type:
                continue

            # Filter by tags
            if tags and not any(t in precedent.tags for t in tags):
                continue

            # Filter by query (simple text search)
            if query:
                query_lower = query.lower()
                searchable = f"{precedent.title} {precedent.description} {precedent.rationale}".lower()
                if query_lower not in searchable:
                    continue

            results.append(precedent)

        # Sort by creation date (newest first)
        results.sort(key=lambda p: p.created_at, reverse=True)

        return results

    def get_by_type(self, precedent_type: PrecedentType) -> list[Precedent]:
        """Get all precedents of a given type."""
        ids = self._by_type.get(precedent_type, [])
        return [self.precedents[pid] for pid in ids if pid in self.precedents]

    def get_by_tag(self, tag: str) -> list[Precedent]:
        """Get all precedents with a given tag."""
        ids = self._by_tag.get(tag, [])
        return [self.precedents[pid] for pid in ids if pid in self.precedents]

    def deprecate(self, precedent_id: str, reason: str = "") -> bool:
        """Mark a precedent as deprecated."""
        precedent = self.get(precedent_id)
        if precedent:
            precedent.status = PrecedentStatus.DEPRECATED
            return True
        return False

    def archive(self, precedent_id: str) -> bool:
        """Archive a precedent."""
        precedent = self.get(precedent_id)
        if precedent:
            precedent.status = PrecedentStatus.ARCHIVED
            return True
        return False

    def export_json(self) -> str:
        """Export all precedents as JSON."""
        data = {
            "precedents": [p.to_dict() for p in self.precedents.values()],
            "exported_at": datetime.now().isoformat(),
        }
        return json.dumps(data, indent=2)

    def import_json(self, json_str: str) -> int:
        """Import precedents from JSON. Returns count of imported precedents."""
        data = json.loads(json_str)
        count = 0

        for p_data in data.get("precedents", []):
            precedent = Precedent.from_dict(p_data)
            self.precedents[precedent.id] = precedent
            self._by_type[precedent.precedent_type].append(precedent.id)

            for tag in precedent.tags:
                if tag not in self._by_tag:
                    self._by_tag[tag] = []
                self._by_tag[tag].append(precedent.id)

            count += 1

        return count

    def format_history(self, limit: int = 10) -> str:
        """Format recent precedent history for display."""
        recent = sorted(
            self.precedents.values(),
            key=lambda p: p.created_at,
            reverse=True
        )[:limit]

        lines = ["## PRECEDENT HISTORY", ""]

        for precedent in recent:
            status_marker = "●" if precedent.status == PrecedentStatus.ACTIVE else "○"
            lines.append(
                f"{status_marker} [{precedent.id}] {precedent.title} "
                f"(Loop {precedent.loop_number})"
            )

        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self.precedents)

    def __str__(self) -> str:
        active = sum(1 for p in self.precedents.values() if p.status == PrecedentStatus.ACTIVE)
        return f"PrecedentLog: {active} active / {len(self)} total precedents"

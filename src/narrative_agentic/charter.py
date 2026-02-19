"""
Charter module - Constitutional framework for AI operating systems.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum


class ArticleType(Enum):
    """Types of constitutional articles."""
    BUDGETARY = "budgetary"
    TRANSPARENCY = "transparency"
    IMMUTABILITY = "immutability"
    PRECEDENT = "precedent"
    IRREVERSIBILITY = "irreversibility"
    INTEGRITY = "integrity"
    CONSULTATION = "consultation"
    CUSTOM = "custom"


@dataclass
class Article:
    """A constitutional article - an invariant rule that cannot be broken."""

    number: int
    name: str
    text: str
    article_type: ArticleType = ArticleType.CUSTOM
    ratified_date: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"Article {self.number}: {self.name}\n> {self.text}"

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "name": self.name,
            "text": self.text,
            "type": self.article_type.value,
            "ratified": self.ratified_date.isoformat(),
        }


@dataclass
class WorldDefinition:
    """The world/institution definition for the system."""

    name: str
    institution_type: str
    aesthetic_era: str
    core_tension: tuple[str, str]
    description: str = ""
    aesthetic_principles: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        tension = f"{self.core_tension[0]} vs {self.core_tension[1]}"
        return f"{self.name} - A {self.institution_type} ({self.aesthetic_era})\nCore Tension: {tension}"


@dataclass
class Amendment:
    """A proposed or ratified amendment to the charter."""

    number: int
    title: str
    description: str
    proposed_by: str
    proposed_date: datetime
    ratified: bool = False
    ratified_date: Optional[datetime] = None
    affected_articles: list[int] = field(default_factory=list)


class Charter:
    """
    The constitutional charter for a Narrative Agentic system.

    This is the founding document that establishes:
    - The world definition
    - Constitutional invariants (articles)
    - Amendment history
    """

    def __init__(
        self,
        world: WorldDefinition,
        version: str = "1.0.0",
    ):
        self.world = world
        self.version = version
        self.articles: list[Article] = []
        self.amendments: list[Amendment] = []
        self.created_at = datetime.now()
        self._sealed = False

    def add_article(self, name: str, text: str, article_type: ArticleType = ArticleType.CUSTOM) -> Article:
        """Add a constitutional article."""
        if self._sealed:
            raise CharterSealedError("Cannot modify sealed charter. Use amendment process.")

        article = Article(
            number=len(self.articles) + 1,
            name=name,
            text=text,
            article_type=article_type,
        )
        self.articles.append(article)
        return article

    def seal(self) -> None:
        """Seal the charter, preventing direct modifications."""
        if not self.articles:
            raise CharterError("Cannot seal charter with no articles.")
        self._sealed = True

    def is_sealed(self) -> bool:
        """Check if the charter is sealed."""
        return self._sealed

    def propose_amendment(
        self,
        title: str,
        description: str,
        proposed_by: str,
        affected_articles: list[int] = None,
    ) -> Amendment:
        """Propose an amendment to the charter."""
        if not self._sealed:
            raise CharterError("Cannot propose amendments to unsealed charter. Modify directly.")

        amendment = Amendment(
            number=len(self.amendments) + 1,
            title=title,
            description=description,
            proposed_by=proposed_by,
            proposed_date=datetime.now(),
            affected_articles=affected_articles or [],
        )
        self.amendments.append(amendment)
        return amendment

    def ratify_amendment(self, amendment_number: int) -> None:
        """Ratify a proposed amendment."""
        for amendment in self.amendments:
            if amendment.number == amendment_number:
                if amendment.ratified:
                    raise CharterError(f"Amendment {amendment_number} already ratified.")
                amendment.ratified = True
                amendment.ratified_date = datetime.now()
                return
        raise CharterError(f"Amendment {amendment_number} not found.")

    def get_article(self, number: int) -> Optional[Article]:
        """Get an article by number."""
        for article in self.articles:
            if article.number == number:
                return article
        return None

    def validate_action(self, action_description: str) -> list[Article]:
        """
        Check which articles might be relevant to a proposed action.
        Returns list of potentially applicable articles for review.
        """
        # This is a simplified check - in practice, you'd want more sophisticated
        # matching logic, possibly using embeddings or LLM-based classification
        relevant = []
        action_lower = action_description.lower()

        keywords_map = {
            ArticleType.BUDGETARY: ["budget", "cost", "expense", "token", "resource"],
            ArticleType.TRANSPARENCY: ["log", "record", "external", "communication"],
            ArticleType.IMMUTABILITY: ["charter", "modify", "change", "constitution"],
            ArticleType.PRECEDENT: ["decision", "precedent", "policy"],
            ArticleType.IRREVERSIBILITY: ["delete", "remove", "irreversible", "permanent"],
            ArticleType.INTEGRITY: ["integrity", "check", "verify", "corrupt"],
            ArticleType.CONSULTATION: ["consult", "crew", "review", "approval"],
        }

        for article in self.articles:
            keywords = keywords_map.get(article.article_type, [])
            if any(kw in action_lower for kw in keywords):
                relevant.append(article)

        return relevant

    def __str__(self) -> str:
        lines = [
            f"{'=' * 60}",
            f"CHARTER: {self.world.name}",
            f"Version: {self.version}",
            f"Status: {'SEALED' if self._sealed else 'DRAFT'}",
            f"{'=' * 60}",
            "",
            "WORLD:",
            str(self.world),
            "",
            "CONSTITUTION:",
        ]

        for article in self.articles:
            lines.append(str(article))
            lines.append("")

        if self.amendments:
            lines.append("AMENDMENTS:")
            for amendment in self.amendments:
                status = "RATIFIED" if amendment.ratified else "PROPOSED"
                lines.append(f"  Amendment {amendment.number}: {amendment.title} [{status}]")

        return "\n".join(lines)


class CharterError(Exception):
    """Base exception for charter operations."""
    pass


class CharterSealedError(CharterError):
    """Raised when attempting to modify a sealed charter."""
    pass


def create_standard_charter(
    name: str,
    institution_type: str,
    aesthetic_era: str,
    core_tension: tuple[str, str],
    description: str = "",
) -> Charter:
    """
    Create a charter with standard articles based on the Narrative Agentic framework.
    """
    world = WorldDefinition(
        name=name,
        institution_type=institution_type,
        aesthetic_era=aesthetic_era,
        core_tension=core_tension,
        description=description,
    )

    charter = Charter(world)

    # Add standard articles
    charter.add_article(
        "Budgetary Sovereignty",
        "No action may exceed its declared resource budget. All expenditures must be logged.",
        ArticleType.BUDGETARY,
    )

    charter.add_article(
        "Transparency Mandate",
        "All external communications must be logged. No covert channels.",
        ArticleType.TRANSPARENCY,
    )

    charter.add_article(
        "Charter Immutability",
        "The Resident Agent cannot modify its own charter. Only Ring 0 may propose amendments.",
        ArticleType.IMMUTABILITY,
    )

    charter.add_article(
        "Precedent Doctrine",
        "Every significant decision must cite existing precedent or establish new precedent.",
        ArticleType.PRECEDENT,
    )

    charter.add_article(
        "Irreversibility Gate",
        "Human approval required for any action that cannot be undone.",
        ArticleType.IRREVERSIBILITY,
    )

    charter.add_article(
        "Integrity Preservation",
        "System must perform integrity checks. Corrupted state must be reported immediately.",
        ArticleType.INTEGRITY,
    )

    charter.add_article(
        "Character Consultation",
        "For non-routine decisions, the Agent must consult relevant crew expertise.",
        ArticleType.CONSULTATION,
    )

    return charter

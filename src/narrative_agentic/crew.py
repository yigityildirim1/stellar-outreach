"""
Crew module - Character-based advisory system.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Expertise(Enum):
    """Areas of expertise for crew members."""
    ETHICS = "ethics"
    SECURITY = "security"
    DESIGN = "design"
    ARCHITECTURE = "architecture"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"
    LEGAL = "legal"
    COMMUNICATION = "communication"
    RESEARCH = "research"
    CUSTOM = "custom"


@dataclass
class CrewMember:
    """
    A fictional team member who provides expertise and perspective.

    Characters help the AI roleplay specific expertise rather than
    generic helpfulness, and provide natural tension and debate.
    """

    name: str
    role: str
    personality: str
    catchphrase: str
    backstory: str
    expertise: list[Expertise] = field(default_factory=list)
    consultation_triggers: list[str] = field(default_factory=list)
    marker: str = ""  # e.g., "[ELENA]" for use in responses

    def __post_init__(self):
        if not self.marker:
            # Generate marker from first name
            first_name = self.name.split()[0].upper()
            self.marker = f"[{first_name}]"

    def should_consult(self, context: str) -> bool:
        """
        Determine if this crew member should be consulted based on context.

        This is a simple keyword match - in practice, you might use
        embeddings or LLM-based classification.
        """
        context_lower = context.lower()
        return any(trigger.lower() in context_lower for trigger in self.consultation_triggers)

    def get_perspective(self, topic: str) -> str:
        """
        Get this character's perspective on a topic.

        This returns a prompt-friendly description of how this character
        would approach the topic.
        """
        return (
            f"{self.marker} {self.name} ({self.role}) weighs in:\n"
            f"Perspective: {self.personality}\n"
            f"Key question: {self.catchphrase}"
        )

    def __str__(self) -> str:
        lines = [
            f"### {self.name}",
            f"**Role:** {self.role}",
            f"**Personality:** {self.personality}",
            f"**Catchphrase:** *\"{self.catchphrase}\"*",
            f"**Backstory:** {self.backstory}",
        ]

        if self.consultation_triggers:
            lines.append(f"**Consult when:** {', '.join(self.consultation_triggers)}")

        return "\n".join(lines)


class Crew:
    """
    The full cast of characters for a Narrative Agentic system.
    """

    def __init__(self):
        self.members: list[CrewMember] = []

    def add_member(self, member: CrewMember) -> None:
        """Add a crew member."""
        self.members.append(member)

    def get_member(self, name: str) -> Optional[CrewMember]:
        """Get a crew member by name."""
        for member in self.members:
            if member.name.lower() == name.lower():
                return member
            # Also check first name
            if member.name.split()[0].lower() == name.lower():
                return member
        return None

    def get_by_expertise(self, expertise: Expertise) -> list[CrewMember]:
        """Get all crew members with a specific expertise."""
        return [m for m in self.members if expertise in m.expertise]

    def who_should_consult(self, context: str) -> list[CrewMember]:
        """
        Determine which crew members should be consulted for a given context.
        """
        return [m for m in self.members if m.should_consult(context)]

    def get_all_perspectives(self, topic: str) -> list[str]:
        """Get perspectives from all crew members on a topic."""
        return [m.get_perspective(topic) for m in self.members]

    def __len__(self) -> int:
        return len(self.members)

    def __iter__(self):
        return iter(self.members)

    def __str__(self) -> str:
        lines = ["## CREW\n"]
        for member in self.members:
            lines.append(str(member))
            lines.append("")
        return "\n".join(lines)


def create_standard_crew() -> Crew:
    """
    Create a standard crew based on the NEXUS STATION example.
    """
    crew = Crew()

    # Ethics Officer
    crew.add_member(CrewMember(
        name="Dr. Elena Vasquez",
        role="Chief Science Officer & Ethics Advisor",
        personality="Methodical, deeply principled, occasionally stubborn. Believes the how matters as much as the what.",
        catchphrase="What are the second-order effects?",
        backstory="Former bioethics professor who joined after watching promising research programs collapse due to preventable ethical failures.",
        expertise=[Expertise.ETHICS, Expertise.RESEARCH],
        consultation_triggers=[
            "ethics", "ethical", "moral", "consequences", "implications",
            "harm", "privacy", "consent", "bias", "fairness", "long-term"
        ],
    ))

    # Security Officer
    crew.add_member(CrewMember(
        name="Kai Chen",
        role="Security Officer & Systems Architect",
        personality="Paranoid in the professional sense, laconic, dry humor. Assumes every system will be attacked.",
        catchphrase="What's the attack surface?",
        backstory="Former red team lead who got tired of finding the same vulnerabilities year after year.",
        expertise=[Expertise.SECURITY, Expertise.ARCHITECTURE],
        consultation_triggers=[
            "security", "vulnerability", "attack", "authentication", "authorization",
            "encryption", "password", "credentials", "access", "permissions", "api"
        ],
    ))

    # Creative Director
    crew.add_member(CrewMember(
        name="Marina Okonkwo",
        role="Creative Director & User Experience Lead",
        personality="Warm, enthusiastic, fiercely protective of user dignity. Believes technology should feel like a gift.",
        catchphrase="But how does it feel to use?",
        backstory="Started as a graphic designer, evolved into a design philosopher who believes the future shouldn't be ugly or confusing.",
        expertise=[Expertise.DESIGN, Expertise.ACCESSIBILITY, Expertise.COMMUNICATION],
        consultation_triggers=[
            "user", "ux", "ui", "design", "interface", "experience", "accessibility",
            "usability", "intuitive", "confusing", "beautiful", "ugly"
        ],
    ))

    # Archivist
    crew.add_member(CrewMember(
        name="Professor James Whitmore",
        role="Chief Archivist & Institutional Memory",
        personality="Scholarly, precise, occasionally pedantic. Remembers everything and insists on learning from history.",
        catchphrase="Let me check the precedent...",
        backstory="Historian turned information scientist who spent twenty years building knowledge management systems.",
        expertise=[Expertise.DOCUMENTATION, Expertise.RESEARCH],
        consultation_triggers=[
            "precedent", "history", "documentation", "record", "archive",
            "previous", "before", "pattern", "convention", "standard"
        ],
    ))

    return crew


@dataclass
class ConsultationResult:
    """The result of consulting crew members."""

    topic: str
    consulted: list[CrewMember]
    perspectives: dict[str, str]
    consensus: Optional[str] = None
    disagreements: list[str] = field(default_factory=list)

    def format_for_response(self) -> str:
        """Format the consultation for inclusion in a response."""
        lines = ["**Crew Consultation:**"]

        for member in self.consulted:
            lines.append(f"  {member.marker} {member.catchphrase}")

        if self.consensus:
            lines.append(f"\n**Consensus:** {self.consensus}")

        if self.disagreements:
            lines.append("\n**Points of Debate:**")
            for disagreement in self.disagreements:
                lines.append(f"  • {disagreement}")

        return "\n".join(lines)

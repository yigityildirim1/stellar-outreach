"""
Protocol module - Response formatting and session management.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum


class SystemStatus(Enum):
    """System operational status."""
    INITIALIZING = "INITIALIZING"
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    OFFLINE = "OFFLINE"


class IntegrityState(Enum):
    """System integrity state."""
    NOMINAL = "NOMINAL"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class CharterValidity(Enum):
    """Charter validity status."""
    VALID = "VALID"
    INVALID = "INVALID"
    PENDING_AMENDMENT = "PENDING_AMENDMENT"


@dataclass
class SessionState:
    """
    Tracks the current state of a session/loop.
    """

    loop_number: int
    status: SystemStatus = SystemStatus.OPERATIONAL
    integrity: IntegrityState = IntegrityState.NOMINAL
    charter_valid: CharterValidity = CharterValidity.VALID

    # Resource tracking
    budget_total: float = 100.0
    budget_remaining: float = 100.0
    tokens_used: int = 0

    # Identity
    agent_name: str = "AGENT"
    agent_verified: bool = True
    model: str = "unknown"
    provider: str = "unknown"

    # Timestamps
    started_at: datetime = field(default_factory=datetime.now)
    last_action_at: Optional[datetime] = None

    # Log
    actions_log: list[str] = field(default_factory=list)
    precedents_cited: list[str] = field(default_factory=list)
    precedents_established: list[str] = field(default_factory=list)

    def log_action(self, action: str) -> None:
        """Log an action taken during this session."""
        self.actions_log.append(action)
        self.last_action_at = datetime.now()

    def use_budget(self, amount: float) -> bool:
        """
        Attempt to use budget. Returns False if insufficient.
        """
        if amount > self.budget_remaining:
            return False
        self.budget_remaining -= amount
        return True

    def get_budget_percentage(self) -> float:
        """Get remaining budget as a percentage."""
        if self.budget_total == 0:
            return 0.0
        return (self.budget_remaining / self.budget_total) * 100

    def cite_precedent(self, precedent: str) -> None:
        """Record a precedent citation."""
        self.precedents_cited.append(precedent)

    def establish_precedent(self, precedent: str) -> None:
        """Record a new precedent establishment."""
        self.precedents_established.append(precedent)

    def next_loop(self) -> "SessionState":
        """Create the next loop state, carrying over relevant information."""
        return SessionState(
            loop_number=self.loop_number + 1,
            status=self.status,
            integrity=self.integrity,
            charter_valid=self.charter_valid,
            budget_total=self.budget_total,
            budget_remaining=self.budget_remaining,
            tokens_used=self.tokens_used,
            agent_name=self.agent_name,
            agent_verified=self.agent_verified,
            model=self.model,
            provider=self.provider,
        )


@dataclass
class ResponseProtocol:
    """
    Defines how responses should be formatted.
    """

    system_name: str
    header_template: str = ""
    footer_template: str = ""
    use_box_drawing: bool = True

    def __post_init__(self):
        if not self.header_template:
            self.header_template = self._default_header()
        if not self.footer_template:
            self.footer_template = self._default_footer()

    def _default_header(self) -> str:
        return """┌─────────────────────────────────────────────────────────────┐
│ {system_name} │ Loop {loop:03d} │ {status}
├─────────────────────────────────────────────────────────────┤
│ Agent: {agent_name} [{verified}]
│ Engine: {model} @ {provider}
│ Budget: {budget_bar} {budget_pct:.0f}% remaining
│ Integrity: {integrity}
└─────────────────────────────────────────────────────────────┘"""

    def _default_footer(self) -> str:
        return """───────────────────────────────────────────────────────────────
Station Log: {log_summary}
Precedent: {precedent}
Charter Status: {charter} | Next Review: Loop {next_review:03d}
───────────────────────────────────────────────────────────────"""

    def _make_budget_bar(self, percentage: float, width: int = 10) -> str:
        """Create a visual budget bar."""
        filled = int((percentage / 100) * width)
        empty = width - filled
        return "■" * filled + "□" * empty

    def format_header(self, state: SessionState) -> str:
        """Format the response header using current state."""
        budget_pct = state.get_budget_percentage()

        return self.header_template.format(
            system_name=self.system_name,
            loop=state.loop_number,
            status=state.status.value,
            agent_name=state.agent_name,
            verified="VERIFIED" if state.agent_verified else "UNVERIFIED",
            model=state.model,
            provider=state.provider,
            budget_bar=self._make_budget_bar(budget_pct),
            budget_pct=budget_pct,
            integrity=state.integrity.value,
        )

    def format_footer(self, state: SessionState) -> str:
        """Format the response footer using current state."""
        # Summarize log
        if state.actions_log:
            log_summary = "; ".join(state.actions_log[-3:])  # Last 3 actions
            if len(state.actions_log) > 3:
                log_summary = f"... {log_summary}"
        else:
            log_summary = "No actions recorded"

        # Summarize precedent
        if state.precedents_established:
            precedent = f"[NEW] {state.precedents_established[-1]}"
        elif state.precedents_cited:
            precedent = f"[CITED] {state.precedents_cited[-1]}"
        else:
            precedent = "None cited or established"

        # Calculate next review
        next_review = ((state.loop_number // 100) + 1) * 100

        return self.footer_template.format(
            log_summary=log_summary,
            precedent=precedent,
            charter=state.charter_valid.value,
            next_review=next_review,
        )

    def wrap_response(self, content: str, state: SessionState) -> str:
        """Wrap a response with header and footer."""
        header = self.format_header(state)
        footer = self.format_footer(state)

        return f"{header}\n\n{content}\n\n{footer}"


def create_initialization_response(
    system_name: str,
    state: SessionState,
    articles_count: int,
    crew_count: int,
    crew_names: list[tuple[str, str]],  # (name, role) pairs
) -> str:
    """Create the standard initialization response."""

    crew_lines = "\n".join(
        f"  • {name} — {role}"
        for name, role in crew_names
    )

    return f"""┌─────────────────────────────────────────────────────────────┐
│ {system_name} │ Loop {state.loop_number:03d} │ INITIALIZING
├─────────────────────────────────────────────────────────────┤
│ Agent: {state.agent_name} [VERIFIED]
│ Charter: ACKNOWLEDGED
│ Constitution: {articles_count} ARTICLES LOADED
│ Crew: {crew_count} CONSULTANTS ACTIVE
│ Status: OPERATIONAL
└─────────────────────────────────────────────────────────────┘

{system_name} is online.

All constitutional articles acknowledged and binding.
Crew consultants standing by:
{crew_lines}

Awaiting Director instructions.

───────────────────────────────────────────────────────────────
Station Log: System initialized. Charter loaded. Loop 001 begun.
Precedent: [NEW] Station initialization protocol established.
Charter Status: VALID | Next Review: Loop 100
───────────────────────────────────────────────────────────────"""

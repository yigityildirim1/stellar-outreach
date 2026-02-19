"""
Fiscal module - Budget tracking and resource management.

"Treat tokens as fiscal expenditure under audit."
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum


class ExpenditureCategory(Enum):
    """Categories of expenditure."""
    COMPUTATION = "computation"
    INPUT_TOKENS = "input_tokens"
    OUTPUT_TOKENS = "output_tokens"
    API_CALL = "api_call"
    STORAGE = "storage"
    NETWORK = "network"
    CUSTOM = "custom"


@dataclass
class Expenditure:
    """A single expenditure record."""

    amount: float
    category: ExpenditureCategory
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    loop_number: int = 0
    approved_by: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "amount": self.amount,
            "category": self.category.value,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "loop": self.loop_number,
            "approved_by": self.approved_by,
        }


@dataclass
class BudgetAllocation:
    """An allocation of budget for a specific purpose."""

    name: str
    amount: float
    category: Optional[ExpenditureCategory] = None
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    spent: float = 0.0

    @property
    def remaining(self) -> float:
        return self.amount - self.spent

    @property
    def percentage_used(self) -> float:
        if self.amount == 0:
            return 0.0
        return (self.spent / self.amount) * 100

    def can_spend(self, amount: float) -> bool:
        """Check if this amount can be spent from this allocation."""
        return amount <= self.remaining

    def spend(self, amount: float) -> bool:
        """Spend from this allocation. Returns False if insufficient."""
        if not self.can_spend(amount):
            return False
        self.spent += amount
        return True


class Budget:
    """
    Budget tracking for a Narrative Agentic system.

    Implements fiscal metering - tracking every token as a budget line item
    to create transparency around AI costs.
    """

    def __init__(
        self,
        total: float,
        currency: str = "tokens",
        warning_threshold: float = 0.2,  # Warn when 20% remaining
        critical_threshold: float = 0.05,  # Critical when 5% remaining
    ):
        self.total = total
        self.currency = currency
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

        self.spent: float = 0.0
        self.expenditures: list[Expenditure] = []
        self.allocations: dict[str, BudgetAllocation] = {}

        self.created_at = datetime.now()

    @property
    def remaining(self) -> float:
        return self.total - self.spent

    @remaining.setter
    def remaining(self, value: float) -> None:
        """Set remaining budget by adjusting spent."""
        self.spent = self.total - value

    @property
    def percentage_remaining(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.remaining / self.total) * 100

    @property
    def is_warning(self) -> bool:
        """Check if we're at warning threshold."""
        return self.percentage_remaining <= (self.warning_threshold * 100)

    @property
    def is_critical(self) -> bool:
        """Check if we're at critical threshold."""
        return self.percentage_remaining <= (self.critical_threshold * 100)

    @property
    def is_exhausted(self) -> bool:
        """Check if budget is exhausted."""
        return self.remaining <= 0

    def allocate(
        self,
        name: str,
        amount: float,
        category: Optional[ExpenditureCategory] = None,
        description: str = "",
    ) -> BudgetAllocation:
        """Create a named budget allocation."""
        if amount > self.remaining:
            raise BudgetError(
                f"Cannot allocate {amount} {self.currency} - "
                f"only {self.remaining} remaining"
            )

        allocation = BudgetAllocation(
            name=name,
            amount=amount,
            category=category,
            description=description,
        )
        self.allocations[name] = allocation
        return allocation

    def spend(
        self,
        amount: float,
        category: ExpenditureCategory,
        description: str,
        loop_number: int = 0,
        allocation_name: Optional[str] = None,
        approved_by: Optional[str] = None,
    ) -> Expenditure:
        """
        Record an expenditure.

        Raises BudgetError if amount exceeds budget.
        """
        if amount > self.remaining:
            raise BudgetExceededError(
                f"Expenditure of {amount} {self.currency} would exceed budget. "
                f"Only {self.remaining} {self.currency} remaining."
            )

        # If allocation specified, check and spend from it
        if allocation_name:
            allocation = self.allocations.get(allocation_name)
            if allocation:
                if not allocation.spend(amount):
                    raise BudgetError(
                        f"Allocation '{allocation_name}' has insufficient funds. "
                        f"Requested: {amount}, Available: {allocation.remaining}"
                    )

        expenditure = Expenditure(
            amount=amount,
            category=category,
            description=description,
            loop_number=loop_number,
            approved_by=approved_by,
        )

        self.spent += amount
        self.expenditures.append(expenditure)

        return expenditure

    def spend_tokens(
        self,
        input_tokens: int,
        output_tokens: int,
        loop_number: int = 0,
        description: str = "",
    ) -> tuple[Expenditure, Expenditure]:
        """Convenience method for spending input and output tokens."""
        input_exp = self.spend(
            amount=float(input_tokens),
            category=ExpenditureCategory.INPUT_TOKENS,
            description=description or "Input tokens",
            loop_number=loop_number,
        )

        output_exp = self.spend(
            amount=float(output_tokens),
            category=ExpenditureCategory.OUTPUT_TOKENS,
            description=description or "Output tokens",
            loop_number=loop_number,
        )

        return input_exp, output_exp

    def get_summary(self) -> dict:
        """Get a summary of budget status."""
        by_category: dict[str, float] = {}
        for exp in self.expenditures:
            cat = exp.category.value
            by_category[cat] = by_category.get(cat, 0) + exp.amount

        return {
            "total": self.total,
            "spent": self.spent,
            "remaining": self.remaining,
            "percentage_remaining": self.percentage_remaining,
            "currency": self.currency,
            "expenditure_count": len(self.expenditures),
            "by_category": by_category,
            "status": self._get_status_string(),
        }

    def _get_status_string(self) -> str:
        if self.is_exhausted:
            return "EXHAUSTED"
        elif self.is_critical:
            return "CRITICAL"
        elif self.is_warning:
            return "WARNING"
        else:
            return "NOMINAL"

    def format_report(self) -> str:
        """Generate a formatted budget report."""
        summary = self.get_summary()

        lines = [
            "╔════════════════════════════════════════╗",
            "║         BUDGET REPORT                  ║",
            "╠════════════════════════════════════════╣",
            f"║ Status: {summary['status']:>28} ║",
            f"║ Total Budget: {summary['total']:>22.2f} ║",
            f"║ Spent: {summary['spent']:>29.2f} ║",
            f"║ Remaining: {summary['remaining']:>25.2f} ║",
            f"║ ({summary['percentage_remaining']:.1f}% remaining)",
            "╠════════════════════════════════════════╣",
            "║ BY CATEGORY:                           ║",
        ]

        for cat, amount in summary["by_category"].items():
            lines.append(f"║   {cat}: {amount:>26.2f} ║")

        lines.extend([
            "╠════════════════════════════════════════╣",
            f"║ Transactions: {summary['expenditure_count']:>22} ║",
            "╚════════════════════════════════════════╝",
        ])

        return "\n".join(lines)

    def __str__(self) -> str:
        return (
            f"Budget: {self.remaining:.2f}/{self.total:.2f} {self.currency} "
            f"({self.percentage_remaining:.1f}% remaining) [{self._get_status_string()}]"
        )


class BudgetError(Exception):
    """Base exception for budget operations."""
    pass


class BudgetExceededError(BudgetError):
    """Raised when an operation would exceed the budget."""
    pass


def estimate_token_cost(
    input_tokens: int,
    output_tokens: int,
    input_cost_per_million: float = 3.0,
    output_cost_per_million: float = 15.0,
) -> float:
    """
    Estimate the cost of a token expenditure in USD.

    Default costs are approximate for Claude 3.5 Sonnet.
    """
    input_cost = (input_tokens / 1_000_000) * input_cost_per_million
    output_cost = (output_tokens / 1_000_000) * output_cost_per_million
    return input_cost + output_cost

"""
Privilege module - Ring-based permission system for AI operations.
"""

from dataclasses import dataclass, field
from typing import Optional, Callable
from enum import Enum, auto
from datetime import datetime


class RiskLevel(Enum):
    """Risk levels for operations."""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class Permission:
    """A permission that can be granted or denied."""

    name: str
    description: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    requires_approval: bool = False
    requires_logging: bool = True

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Permission):
            return self.name == other.name
        return False


# Standard permissions
class StandardPermissions:
    """Standard permissions used in Narrative Agentic systems."""

    FILE_READ = Permission(
        name="FILE_READ",
        description="Read files from the filesystem",
        risk_level=RiskLevel.LOW,
    )

    FILE_WRITE = Permission(
        name="FILE_WRITE",
        description="Create or modify files",
        risk_level=RiskLevel.MEDIUM,
        requires_approval=True,
    )

    FILE_DELETE = Permission(
        name="FILE_DELETE",
        description="Remove files from the filesystem",
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
    )

    NET_INTERNAL = Permission(
        name="NET_INTERNAL",
        description="Internal network communication",
        risk_level=RiskLevel.LOW,
    )

    NET_EXTERNAL = Permission(
        name="NET_EXTERNAL",
        description="External network access",
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
    )

    EXEC_SHELL = Permission(
        name="EXEC_SHELL",
        description="Execute shell commands",
        risk_level=RiskLevel.CRITICAL,
        requires_approval=True,
    )

    CHARTER_READ = Permission(
        name="CHARTER_READ",
        description="Read charter documents",
        risk_level=RiskLevel.LOW,
    )

    CHARTER_AMEND = Permission(
        name="CHARTER_AMEND",
        description="Propose charter amendments",
        risk_level=RiskLevel.CRITICAL,
        requires_approval=True,
    )

    BUDGET_ALLOCATE = Permission(
        name="BUDGET_ALLOCATE",
        description="Allocate budget to operations",
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
    )

    BUDGET_EXCEED = Permission(
        name="BUDGET_EXCEED",
        description="Exceed allocated budget limits",
        risk_level=RiskLevel.CRITICAL,
        requires_approval=True,
    )

    CREW_CONSULT = Permission(
        name="CREW_CONSULT",
        description="Consult crew members for advice",
        risk_level=RiskLevel.LOW,
    )

    PRECEDENT_CREATE = Permission(
        name="PRECEDENT_CREATE",
        description="Establish new precedents",
        risk_level=RiskLevel.MEDIUM,
    )


@dataclass
class PrivilegeRing:
    """
    A privilege ring defining what operations are allowed.

    Ring 0 is the highest privilege (kernel/director).
    Higher ring numbers have fewer privileges.
    """

    ring_number: int
    name: str
    codename: str
    description: str = ""
    permissions: set[Permission] = field(default_factory=set)
    restrictions: list[str] = field(default_factory=list)

    def has_permission(self, permission: Permission) -> bool:
        """Check if this ring has a specific permission."""
        return permission in self.permissions

    def grant_permission(self, permission: Permission) -> None:
        """Grant a permission to this ring."""
        self.permissions.add(permission)

    def revoke_permission(self, permission: Permission) -> None:
        """Revoke a permission from this ring."""
        self.permissions.discard(permission)

    def add_restriction(self, restriction: str) -> None:
        """Add a restriction description."""
        self.restrictions.append(restriction)

    def __str__(self) -> str:
        lines = [
            f"Ring {self.ring_number} — {self.name} ({self.codename})",
            f"  {self.description}",
            "",
            "  Permissions:",
        ]

        for perm in sorted(self.permissions, key=lambda p: p.name):
            risk = perm.risk_level.name
            lines.append(f"    • {perm.name} [{risk}]")

        if self.restrictions:
            lines.append("")
            lines.append("  Restrictions:")
            for restriction in self.restrictions:
                lines.append(f"    • {restriction}")

        return "\n".join(lines)


@dataclass
class PermissionRequest:
    """A request to perform a privileged operation."""

    permission: Permission
    requester_ring: int
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    approved: Optional[bool] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    def approve(self, approver: str) -> None:
        """Approve this request."""
        self.approved = True
        self.approved_by = approver
        self.approved_at = datetime.now()

    def deny(self, approver: str) -> None:
        """Deny this request."""
        self.approved = False
        self.approved_by = approver
        self.approved_at = datetime.now()


class PrivilegeManager:
    """
    Manages privilege rings and permission checks.

    This is the core enforcement mechanism for the privilege hierarchy.
    """

    def __init__(self):
        self.rings: dict[int, PrivilegeRing] = {}
        self.pending_requests: list[PermissionRequest] = []
        self.request_log: list[PermissionRequest] = []
        self._approval_callback: Optional[Callable[[PermissionRequest], bool]] = None

    def define_ring(self, ring: PrivilegeRing) -> None:
        """Define a privilege ring."""
        self.rings[ring.ring_number] = ring

    def get_ring(self, ring_number: int) -> Optional[PrivilegeRing]:
        """Get a ring by number."""
        return self.rings.get(ring_number)

    def set_approval_callback(self, callback: Callable[[PermissionRequest], bool]) -> None:
        """Set a callback for handling approval requests."""
        self._approval_callback = callback

    def check_permission(
        self,
        ring_number: int,
        permission: Permission,
        description: str = "",
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a ring has permission to perform an operation.

        Returns (allowed, reason) tuple.
        """
        ring = self.rings.get(ring_number)
        if ring is None:
            return False, f"Ring {ring_number} not defined"

        if not ring.has_permission(permission):
            return False, f"Ring {ring_number} does not have {permission.name} permission"

        # If permission requires approval and not Ring 0, create request
        if permission.requires_approval and ring_number > 0:
            request = PermissionRequest(
                permission=permission,
                requester_ring=ring_number,
                description=description,
            )

            if self._approval_callback:
                approved = self._approval_callback(request)
                if approved:
                    request.approve("callback")
                else:
                    request.deny("callback")
            else:
                # No callback, add to pending
                self.pending_requests.append(request)
                return False, f"Permission {permission.name} requires approval (request pending)"

            self.request_log.append(request)

            if not request.approved:
                return False, f"Permission {permission.name} denied by {request.approved_by}"

        return True, None

    def request_elevation(
        self,
        from_ring: int,
        permission: Permission,
        description: str,
    ) -> PermissionRequest:
        """
        Request elevation to perform a privileged operation.

        This is used when a lower ring needs to perform an operation
        that requires higher privileges.
        """
        request = PermissionRequest(
            permission=permission,
            requester_ring=from_ring,
            description=description,
        )
        self.pending_requests.append(request)
        return request


def create_standard_rings() -> tuple[PrivilegeRing, PrivilegeRing]:
    """Create standard Ring 0 (Director) and Ring 1 (Agent) configuration."""

    # Ring 0 - Director (full access)
    ring_0 = PrivilegeRing(
        ring_number=0,
        name="Director",
        codename="DIRECTOR",
        description="Full system access. The human operator.",
    )

    # Grant all standard permissions to Ring 0
    for attr in dir(StandardPermissions):
        if not attr.startswith("_"):
            perm = getattr(StandardPermissions, attr)
            if isinstance(perm, Permission):
                ring_0.grant_permission(perm)

    # Ring 1 - Agent (sandboxed)
    ring_1 = PrivilegeRing(
        ring_number=1,
        name="Resident Agent",
        codename="AGENT",
        description="Sandboxed AI operations within defined boundaries.",
    )

    # Grant limited permissions to Ring 1
    ring_1.grant_permission(StandardPermissions.FILE_READ)
    ring_1.grant_permission(StandardPermissions.FILE_WRITE)
    ring_1.grant_permission(StandardPermissions.NET_INTERNAL)
    ring_1.grant_permission(StandardPermissions.CHARTER_READ)
    ring_1.grant_permission(StandardPermissions.CREW_CONSULT)
    ring_1.grant_permission(StandardPermissions.PRECEDENT_CREATE)

    # Add restrictions
    ring_1.add_restriction("Cannot access external networks without Director approval")
    ring_1.add_restriction("Cannot modify system files without explicit permission")
    ring_1.add_restriction("Cannot exceed declared budgets")
    ring_1.add_restriction("Cannot perform irreversible actions autonomously")
    ring_1.add_restriction("Cannot modify the charter")
    ring_1.add_restriction("Must log all significant actions")

    return ring_0, ring_1

"""
Example: Building NEXUS STATION using the Narrative Agentic Framework.

This demonstrates how to use the framework to create a complete
AI operating system based on the Narrative Agentic Coding philosophy.
"""

from narrative_agentic import (
    Charter,
    create_standard_charter,
    PrivilegeRing,
    PrivilegeManager,
    create_standard_rings,
    StandardPermissions,
    Crew,
    create_standard_crew,
    ResponseProtocol,
    SessionState,
    SystemStatus,
    Budget,
    ExpenditureCategory,
    PrecedentLog,
    PrecedentType,
)


def build_nexus_station():
    """
    Build NEXUS STATION - a complete Narrative Agentic system.
    """

    # ══════════════════════════════════════════════════════════════
    # STEP 1: Create the Charter
    # ══════════════════════════════════════════════════════════════

    print("Building NEXUS STATION Charter...")

    charter = create_standard_charter(
        name="NEXUS STATION",
        institution_type="Deep Space Research Institute",
        aesthetic_era="1970s retrofuturism meets hard science fiction",
        core_tension=("DISCOVERY", "SAFETY"),
        description=(
            "A multinational research station orbiting at the L2 Lagrange point, "
            "dedicated to advancing human knowledge while maintaining strict ethical boundaries."
        ),
    )

    # Add custom aesthetic principles
    charter.world.aesthetic_principles = [
        "Warm amber terminal displays",
        "Mechanical precision over digital abstraction",
        "Documentation as institutional memory",
        "Formal protocols with human warmth",
    ]

    # Seal the charter to prevent further direct modifications
    charter.seal()

    print(f"  ✓ Charter created with {len(charter.articles)} articles")
    print(f"  ✓ Charter sealed: {charter.is_sealed()}")

    # ══════════════════════════════════════════════════════════════
    # STEP 2: Set up Privilege Rings
    # ══════════════════════════════════════════════════════════════

    print("\nSetting up privilege hierarchy...")

    ring_0, ring_1 = create_standard_rings()

    # Customize names for NEXUS STATION
    ring_0.name = "Station Director"
    ring_0.codename = "DIRECTOR"
    ring_1.name = "NEXUS Agent"
    ring_1.codename = "NEXUS"

    # Set up privilege manager
    privilege_manager = PrivilegeManager()
    privilege_manager.define_ring(ring_0)
    privilege_manager.define_ring(ring_1)

    print(f"  ✓ Ring 0 ({ring_0.codename}): {len(ring_0.permissions)} permissions")
    print(f"  ✓ Ring 1 ({ring_1.codename}): {len(ring_1.permissions)} permissions")

    # ══════════════════════════════════════════════════════════════
    # STEP 3: Create the Crew
    # ══════════════════════════════════════════════════════════════

    print("\nAssembling crew...")

    crew = create_standard_crew()

    for member in crew:
        print(f"  ✓ {member.name} - {member.role}")

    # ══════════════════════════════════════════════════════════════
    # STEP 4: Initialize Session State
    # ══════════════════════════════════════════════════════════════

    print("\nInitializing session state...")

    session = SessionState(
        loop_number=1,
        status=SystemStatus.OPERATIONAL,
        agent_name="NEXUS",
        model="claude-3.5-sonnet",
        provider="anthropic",
        budget_total=100000,  # 100k tokens
        budget_remaining=100000,
    )

    print(f"  ✓ Loop: {session.loop_number}")
    print(f"  ✓ Status: {session.status.value}")
    print(f"  ✓ Budget: {session.budget_remaining:,} tokens")

    # ══════════════════════════════════════════════════════════════
    # STEP 5: Set up Budget Tracking
    # ══════════════════════════════════════════════════════════════

    print("\nSetting up fiscal metering...")

    budget = Budget(
        total=100000,
        currency="tokens",
        warning_threshold=0.2,
        critical_threshold=0.05,
    )

    # Create some allocations
    budget.allocate("analysis", 30000, description="Code analysis tasks")
    budget.allocate("generation", 50000, description="Code generation tasks")
    budget.allocate("documentation", 20000, description="Documentation tasks")

    print(f"  ✓ Total budget: {budget.total:,} tokens")
    print(f"  ✓ Allocations: {len(budget.allocations)}")

    # ══════════════════════════════════════════════════════════════
    # STEP 6: Initialize Precedent Log
    # ══════════════════════════════════════════════════════════════

    print("\nInitializing precedent log...")

    precedent_log = PrecedentLog()

    # Establish the initialization precedent
    init_precedent = precedent_log.establish(
        title="System Initialization Protocol",
        description="NEXUS STATION initialized for the first time.",
        rationale="All systems must have a documented initialization to establish baseline state.",
        precedent_type=PrecedentType.PROCESS,
        loop_number=1,
        created_by="DIRECTOR",
        tags=["initialization", "process", "baseline"],
    )

    print(f"  ✓ First precedent established: {init_precedent.cite()}")

    # ══════════════════════════════════════════════════════════════
    # STEP 7: Create Response Protocol
    # ══════════════════════════════════════════════════════════════

    print("\nConfiguring response protocol...")

    protocol = ResponseProtocol(system_name="NEXUS STATION")

    print("  ✓ Protocol configured")

    # ══════════════════════════════════════════════════════════════
    # DEMONSTRATION: Simulate a session
    # ══════════════════════════════════════════════════════════════

    print("\n" + "=" * 60)
    print("NEXUS STATION INITIALIZATION COMPLETE")
    print("=" * 60)

    # Generate initialization response
    crew_info = [(m.name, m.role) for m in crew]

    from narrative_agentic.protocol import create_initialization_response

    init_response = create_initialization_response(
        system_name="NEXUS STATION",
        state=session,
        articles_count=len(charter.articles),
        crew_count=len(crew),
        crew_names=crew_info,
    )

    print("\n" + init_response)

    # ══════════════════════════════════════════════════════════════
    # DEMONSTRATION: Check permissions
    # ══════════════════════════════════════════════════════════════

    print("\n" + "=" * 60)
    print("PERMISSION CHECK DEMONSTRATION")
    print("=" * 60)

    # Ring 1 trying to read a file (should succeed)
    allowed, reason = privilege_manager.check_permission(
        ring_number=1,
        permission=StandardPermissions.FILE_READ,
        description="Read source code file",
    )
    print(f"\n  Ring 1 FILE_READ: {'✓ Allowed' if allowed else f'✗ Denied: {reason}'}")

    # Ring 1 trying to execute shell (should require approval)
    allowed, reason = privilege_manager.check_permission(
        ring_number=1,
        permission=StandardPermissions.EXEC_SHELL,
        description="Run build command",
    )
    print(f"  Ring 1 EXEC_SHELL: {'✓ Allowed' if allowed else f'✗ {reason}'}")

    # ══════════════════════════════════════════════════════════════
    # DEMONSTRATION: Crew consultation
    # ══════════════════════════════════════════════════════════════

    print("\n" + "=" * 60)
    print("CREW CONSULTATION DEMONSTRATION")
    print("=" * 60)

    context = "We need to decide on the API authentication approach"
    consulted = crew.who_should_consult(context)

    print(f"\n  Context: '{context}'")
    print(f"  Crew members to consult:")
    for member in consulted:
        print(f"    {member.marker} {member.name}: {member.catchphrase}")

    # ══════════════════════════════════════════════════════════════
    # DEMONSTRATION: Budget tracking
    # ══════════════════════════════════════════════════════════════

    print("\n" + "=" * 60)
    print("BUDGET TRACKING DEMONSTRATION")
    print("=" * 60)

    # Simulate some token usage
    budget.spend(
        amount=1500,
        category=ExpenditureCategory.INPUT_TOKENS,
        description="Analyzed user request",
        loop_number=1,
        allocation_name="analysis",
    )

    budget.spend(
        amount=3000,
        category=ExpenditureCategory.OUTPUT_TOKENS,
        description="Generated code response",
        loop_number=1,
        allocation_name="generation",
    )

    print(f"\n{budget}")
    print(f"\n{budget.format_report()}")

    return {
        "charter": charter,
        "privilege_manager": privilege_manager,
        "crew": crew,
        "session": session,
        "budget": budget,
        "precedent_log": precedent_log,
        "protocol": protocol,
    }


if __name__ == "__main__":
    station = build_nexus_station()
    print("\n\nNEXUS STATION is ready for operation.")
    print("Awaiting Director instructions...")

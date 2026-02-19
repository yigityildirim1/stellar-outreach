#!/usr/bin/env python3
"""
NEXUS STATION Demo

Demonstrates the API integration with the Narrative Agentic framework.
Shows how the system routes different tasks to different APIs.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from narrative_agentic import (
    create_nexus_agent,
    auto_configure_with_defaults,
    TaskType,
)


def print_separator():
    print("=" * 70)


def demo_coding_task():
    """Demonstrate a coding task routed to OpenAI."""
    print_separator()
    print("DEMO 1: CODING TASK → OpenAI GPT-4o")
    print_separator()
    print()
    
    agent = create_nexus_agent()
    
    message = "Write a Python function to implement a binary search algorithm"
    print(f"[DIRECTOR] {message}")
    print()
    
    # Show task detection
    task_type = agent._determine_task_type(message)
    print(f"Detected task type: {task_type.value}")
    print()
    
    # Show crew consultation
    consulted = agent._consult_crew(message, task_type)
    print("Crew to consult:")
    for member in consulted:
        print(f"  • {member.name} - {member.catchphrase}")
    print()
    
    # Get response
    print("[NEXUS] Generating response...")
    print()
    
    response = agent.process(message)
    
    print(f"Response from: {response.from_api} ({response.model})")
    print(f"Tokens used: {int(response.budget_spent)}")
    print()
    print("Response content:")
    print("─" * 70)
    print(response.content)
    print("─" * 70)
    print()


def demo_general_task():
    """Demonstrate a general task routed to Gemini."""
    print_separator()
    print("DEMO 2: GENERAL TASK → Gemini Pro")
    print_separator()
    print()
    
    agent = create_nexus_agent()
    
    message = "Explain the concept of retrofuturism in art and design"
    print(f"[DIRECTOR] {message}")
    print()
    
    # Show task detection
    task_type = agent._determine_task_type(message)
    print(f"Detected task type: {task_type.value}")
    print()
    
    # Show crew consultation
    consulted = agent._consult_crew(message, task_type)
    print("Crew to consult:")
    for member in consulted:
        print(f"  • {member.name} - {member.catchphrase}")
    print()
    
    # Get response
    print("[NEXUS] Generating response...")
    print()
    
    response = agent.process(message)
    
    print(f"Response from: {response.from_api} ({response.model})")
    print(f"Tokens used: {int(response.budget_spent)}")
    print()
    print("Response content:")
    print("─" * 70)
    print(response.content)
    print("─" * 70)
    print()


def demo_security_consultation():
    """Demonstrate security crew consultation."""
    print_separator()
    print("DEMO 3: SECURITY-RELATED CODING → OpenAI + Kai Consultation")
    print_separator()
    print()
    
    agent = create_nexus_agent()
    
    message = "Write a Python API endpoint that handles user authentication"
    print(f"[DIRECTOR] {message}")
    print()
    
    task_type = agent._determine_task_type(message)
    consulted = agent._consult_crew(message, task_type)
    
    print("Security-related keywords detected: 'authentication'")
    print()
    print("Crew to consult:")
    for member in consulted:
        print(f"  • {member.name} - {member.catchphrase}")
    print()
    
    response = agent.process(message)
    
    print(f"Response from: {response.from_api} ({response.model})")
    print(f"Crew consulted: {', '.join(response.crew_consulted)}")
    print()
    print("Response content:")
    print("─" * 70)
    print(response.content)
    print("─" * 70)
    print()


def demo_status():
    """Show system status."""
    print_separator()
    print("SYSTEM STATUS")
    print_separator()
    print()
    
    agent = create_nexus_agent()
    status = agent.get_status()
    
    print(f"Loop: {status['loop']}")
    print(f"Status: {status['status']}")
    print(f"Integrity: {status['integrity']}")
    print(f"Budget: {status['budget']}")
    print(f"Crew: {status['crew_count']} members")
    print(f"Precedents: {status['precedents']} established")
    print()
    
    print("API Status:")
    for api, configured in status['apis'].items():
        status_str = "✓ Configured" if configured else "✗ Not configured"
        print(f"  {api}: {status_str}")
    print()


def main():
    """Run the demo."""
    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║                                                                  ║")
    print("║   ◈ N E X U S   S T A T I O N                                    ║")
    print("║   API Integration Demo                                           ║")
    print("║                                                                  ║")
    print("╠══════════════════════════════════════════════════════════════════╣")
    print("║   Routing: Coding → OpenAI GPT-4o                                ║")
    print("║            General → Gemini Pro                                  ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()
    
    # Ensure APIs are configured
    from narrative_agentic.config import get_config_manager
    config_status = get_config_manager().is_configured()
    
    if not config_status['fully_configured']:
        print("Configuring APIs...")
        auto_configure_with_defaults()
        print()
    
    # Run demos
    try:
        demo_status()
        
        input("Press Enter to run CODING task demo...")
        demo_coding_task()
        
        input("Press Enter to run GENERAL task demo...")
        demo_general_task()
        
        input("Press Enter to run SECURITY consultation demo...")
        demo_security_consultation()
        
        print_separator()
        print("Demo complete!")
        print_separator()
        print()
        
    except KeyboardInterrupt:
        print()
        print("Demo interrupted.")
        print()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
NEXUS STATION CLI

Command-line interface for interacting with the NEXUS agent.
"""

import sys
import os
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from narrative_agentic import (
    create_nexus_agent,
    NexusAgent,
    configure_apis,
    auto_configure_with_defaults,
    get_api_config,
    get_config_manager,
    TaskType,
)


def print_header():
    """Print the NEXUS STATION header."""
    print()
    print("==============================================================")
    print()
    print("   N E X U S   S T A T I O N                                  ")
    print("   Deep Space Research & Development Institute                ")
    print("   Est. 2147 | Charter Revision: 001                          ")
    print()
    print("==============================================================")
    print("   Coding tasks -> OpenAI gpt-5.2-codex-mini                  ")
    print("   General tasks -> Gemini gemini-3-flash-preview             ")
    print("==============================================================")
    print()


def print_status(agent: NexusAgent):
    """Print current agent status."""
    status = agent.get_status()
    
    print("+-------------------------------------------------------------+")
    print("| Loop {:03d} | {:12} | Integrity: {:7}      |".format(
        status['loop'], status['status'].upper(), status['integrity'][:7]
    ))
    print("+-------------------------------------------------------------+")
    budget_str = status['budget'][:40]
    print("| Budget: {:40}      |".format(budget_str))
    print("| Crew: {} active | Precedents: {:3}                       |".format(
        status['crew_count'], status['precedents']
    ))
    print("+-------------------------------------------------------------+")
    print()


def interactive_mode(agent: NexusAgent):
    """Run interactive chat mode."""
    print_header()
    print_status(agent)
    
    print("Type 'help' for commands, 'exit' to quit.")
    print("-" * 60)
    print()
    
    while True:
        try:
            # Get input
            message = input("[DIRECTOR] > ").strip()
            
            if not message:
                continue
            
            # Handle commands
            if message.lower() in ('exit', 'quit', 'q'):
                print()
                print("NEXUS STATION shutting down. Goodbye, Director.")
                break
            
            if message.lower() in ('help', 'h', '?'):
                print_help()
                continue
            
            if message.lower() == 'status':
                print_status(agent)
                continue
            
            if message.lower() == 'crew':
                print_crew(agent)
                continue
            
            if message.lower() == 'config':
                print_config()
                continue
            
            # Process message
            print()
            print("[NEXUS] Processing...")
            print()
            
            response = agent.process(message)
            
            # Check if this is a direct crew response
            if response.direct_crew_response:
                # User asked a specific crew member directly
                cr = response.direct_crew_response
                print()
                print("=" * 60)
                print("  DIRECT CREW RESPONSE")
                print("=" * 60)
                print()
                print("  {} {} ({})".format(cr.marker, cr.name, cr.role))
                print('  Catchphrase: "{}"'.format(cr.catchphrase))
                print()
                print("  {}".format(cr.content))
                print()
                print("=" * 60)
            elif response.crew_responses:
                # Normal flow with crew consultation
                print()
                print("  --- CREW CONSULTATION ---")
                for cr in response.crew_responses:
                    print()
                    print("  {} {} ({})".format(cr.marker, cr.name, cr.role))
                    print('  "{}"'.format(cr.catchphrase))
                    print("  >> {}".format(cr.content))
                print()
                print("  --- END CREW CONSULTATION ---")
                print()
                # Print NEXUS response
                print("[NEXUS] {}".format(response.content))
            else:
                # No crew consultation
                print("[NEXUS] {}".format(response.content))
            
            print()
            
            # Print metadata
            print("  API: {} | Model: {}".format(response.from_api, response.model))
            
            if response.budget_spent > 0:
                print("  Tokens used: {}".format(int(response.budget_spent)))
            
            if response.precedent_established:
                print("  Precedent: {}".format(response.precedent_established))
            
            print()
            print("-" * 60)
            print()
            
            # Next loop
            agent.next_loop()
            
        except KeyboardInterrupt:
            print()
            print()
            print("NEXUS STATION shutting down. Goodbye, Director.")
            break
        except Exception as e:
            print()
            print("[WARNING] Error: {}".format(e))
            print()


def print_help():
    """Print help message."""
    print()
    print("Commands:")
    print("  help      - Show this help message")
    print("  status    - Show current system status")
    print("  crew      - List crew members")
    print("  config    - Show API configuration")
    print("  exit      - Exit NEXUS STATION")
    print()
    print("Routing:")
    print("  - Coding tasks -> OpenAI gpt-5.2-codex-mini")
    print("  - General tasks -> Gemini gemini-3-flash-preview")
    print()
    print("Examples:")
    print('  Write a Python function to calculate fibonacci numbers')
    print('  Explain quantum computing')
    print('  Review this code for security issues')
    print()


def print_crew(agent: NexusAgent):
    """Print crew information."""
    print()
    print("CREW CONSULTANTS:")
    print()
    
    for member in agent.crew:
        print("  {} {}".format(member.marker, member.name))
        print("     Role: {}".format(member.role))
        print("     Catchphrase: {}".format(member.catchphrase))
        print()
    
    print("-" * 60)
    print()


def print_config():
    """Print configuration status."""
    config = get_api_config()
    status = get_config_manager().is_configured()
    
    print()
    print("API CONFIGURATION:")
    print()
    print("  OpenAI:")
    print("    Configured: {}".format("Yes" if status['openai'] else "No"))
    print("    Model: {}".format(config.openai_coding_model))
    print("    Base URL: {}".format(config.openai_base_url))
    print()
    print("  Gemini:")
    print("    Configured: {}".format("Yes" if status['gemini'] else "No"))
    print("    Model: {}".format(config.gemini_general_model))
    print()
    print("  Usage Statistics:")
    print("    OpenAI requests: {}".format(config.total_requests_openai))
    print("    OpenAI tokens: {:,}".format(config.total_tokens_openai))
    print("    Gemini requests: {}".format(config.total_requests_gemini))
    print("    Gemini tokens: {:,}".format(config.total_tokens_gemini))
    print()
    print("-" * 60)
    print()


def quick_mode(message: str):
    """Process a single message and exit."""
    print_header()
    
    agent = create_nexus_agent()
    
    ready = agent.is_ready()
    if not ready['ready']:
        print("[WARNING] APIs not configured. Running setup...")
        auto_configure_with_defaults()
        agent = create_nexus_agent()
    
    response = agent.process(message)
    
    print("[NEXUS] {}".format(response.content))
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="NEXUS STATION - Narrative Agentic AI System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py                    # Interactive mode
  python cli.py -m "Hello"         # Quick message
  python cli.py -m "Write a Python function"  # Coding task -> OpenAI
  python cli.py setup              # Configure APIs
        """
    )
    
    parser.add_argument(
        '-m', '--message',
        help='Send a single message and exit'
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        choices=['setup', 'status'],
        help='Special command to run'
    )
    
    args = parser.parse_args()
    
    # Handle setup command
    if args.command == 'setup':
        auto_configure_with_defaults()
        return
    
    # Handle status command
    if args.command == 'status':
        print_header()
        agent = create_nexus_agent()
        print_status(agent)
        print_config()
        return
    
    # Quick message mode
    if args.message:
        quick_mode(args.message)
        return
    
    # Interactive mode
    agent = create_nexus_agent()
    
    # Check if configured
    ready = agent.is_ready()
    if not ready['ready']:
        print("[WARNING] APIs not configured. Running setup...")
        print()
        auto_configure_with_defaults()
        print()
        # Recreate agent after setup
        agent = create_nexus_agent()
    
    interactive_mode(agent)


if __name__ == "__main__":
    main()

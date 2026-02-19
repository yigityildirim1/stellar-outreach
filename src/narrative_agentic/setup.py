#!/usr/bin/env python3
"""
NEXUS STATION Setup Script

Run this once to configure API keys permanently.
The keys will be stored in ~/.nexus_station/config.json
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from narrative_agentic import auto_configure_with_defaults, get_api_config, get_config_manager


def main():
    """Run the setup and configure APIs."""
    print("")
    print("==============================================================")
    print("")
    print("   N E X U S   S T A T I O N                                  ")
    print("   API Configuration Setup                                    ")
    print("")
    print("==============================================================")
    print("")
    
    # Check current config
    config = get_api_config()
    
    print("Current configuration:")
    print("  OpenAI API: {}".format("Configured" if config.openai_api_key else "Not configured"))
    print("  Gemini API: {}".format("Configured" if config.gemini_api_key else "Not configured"))
    print("")
    
    # Auto-configure with defaults
    print("Configuring with provided API keys...")
    print("")
    
    auto_configure_with_defaults()
    
    print("")
    print("Configuration saved to:", get_config_manager().config_path)
    print("")
    
    # Show new config
    config = get_api_config()
    print("Updated configuration:")
    print("  OpenAI Model:", config.openai_coding_model)
    print("  Gemini Model:", config.gemini_general_model)
    print("")
    print("Routing configuration:")
    print("  - Coding tasks -> OpenAI gpt-5.2-codex-mini")
    print("  - General tasks -> Gemini gemini-3-flash-preview")
    print("")
    print("==============================================================")
    print("   Setup complete! You can now use NEXUS STATION.             ")
    print("                                                              ")
    print("   Model Versions:                                            ")
    print("   - OpenAI: gpt-5.2-codex-mini                               ")
    print("   - Gemini: gemini-3-flash-preview                           ")
    print("==============================================================")
    print("")


if __name__ == "__main__":
    main()

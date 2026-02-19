"""
Configuration module for persistent API key and settings storage.

Stores configuration in a JSON file in the user's home directory.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


DEFAULT_CONFIG_DIR = Path.home() / ".nexus_station"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


@dataclass
class APIConfig:
    """Configuration for API keys and settings."""
    
    # OpenAI API configuration
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"  # GPT-4o (latest)
    openai_coding_model: str = "gpt-4o"  # GPT-4o for coding
    
    # Gemini API configuration
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"  # Gemini 3 Flash Preview
    gemini_general_model: str = "gemini-3-flash-preview"  # Gemini 3 Flash Preview for general
    
    # Routing preferences
    use_openai_for_coding: bool = True
    use_gemini_for_general: bool = True
    
    # Usage tracking
    total_requests_openai: int = 0
    total_requests_gemini: int = 0
    total_tokens_openai: int = 0
    total_tokens_gemini: int = 0
    
    # Budget tracking - PERSISTENT
    budget_total: float = 100000.0
    budget_remaining: float = 100000.0
    budget_currency: str = "tokens"

    # Workspace directory for file operations
    workspace_dir: str = ""
    
    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "APIConfig":
        """Create config from dictionary."""
        return cls(**data)
    
    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "APIConfig":
        """Create config from dictionary."""
        return cls(**data)


class ConfigManager:
    """
    Manages persistent configuration for NEXUS STATION.
    
    Stores API keys and preferences so they persist across sessions.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_FILE
        self._config: Optional[APIConfig] = None
        
    def _ensure_config_dir(self) -> None:
        """Ensure the config directory exists."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
    def load(self) -> APIConfig:
        """Load configuration from file."""
        if self._config is not None:
            return self._config
            
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                self._config = APIConfig.from_dict(data)
            except (json.JSONDecodeError, TypeError) as e:
                print(f"[WARNING] Could not load config: {e}")
                self._config = APIConfig()
        else:
            self._config = APIConfig()
            
        return self._config
    
    def save(self, config: Optional[APIConfig] = None) -> None:
        """Save configuration to file."""
        if config is None:
            config = self._config
        if config is None:
            raise ValueError("No config to save")
            
        self._ensure_config_dir()
        
        with open(self.config_path, 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
            
        self._config = config
        
    def get_config(self) -> APIConfig:
        """Get current configuration (loads if needed)."""
        if self._config is None:
            return self.load()
        return self._config
    
    def update_openai_key(self, api_key: str) -> None:
        """Update OpenAI API key."""
        config = self.get_config()
        config.openai_api_key = api_key
        self.save(config)
        
    def update_gemini_key(self, api_key: str) -> None:
        """Update Gemini API key."""
        config = self.get_config()
        config.gemini_api_key = api_key
        self.save(config)
    
    def is_configured(self) -> dict:
        """Check which APIs are configured."""
        config = self.get_config()
        return {
            "openai": bool(config.openai_api_key),
            "gemini": bool(config.gemini_api_key),
            "fully_configured": bool(config.openai_api_key and config.gemini_api_key),
        }
    
    def increment_usage(self, api: str, tokens: int = 0) -> None:
        """Increment usage counters."""
        config = self.get_config()
        if api == "openai":
            config.total_requests_openai += 1
            config.total_tokens_openai += tokens
        elif api == "gemini":
            config.total_requests_gemini += 1
            config.total_tokens_gemini += tokens
        self.save(config)


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def configure_apis(openai_key: Optional[str] = None, gemini_key: Optional[str] = None) -> None:
    """
    Configure API keys. Call this once to persist configuration.
    
    Args:
        openai_key: OpenAI API key (optional)
        gemini_key: Gemini API key (optional)
    """
    manager = get_config_manager()
    config = manager.get_config()
    
    if openai_key:
        config.openai_api_key = openai_key
    if gemini_key:
        config.gemini_api_key = gemini_key
        
    manager.save(config)
    print("[OK] API configuration saved successfully!")
    print("  OpenAI:", "Configured" if config.openai_api_key else "Not configured")
    print("  Gemini:", "Configured" if config.gemini_api_key else "Not configured")


def auto_configure_with_defaults() -> None:
    """
    Auto-configure with the provided API keys.
    This sets up the system with the user's keys permanently.
    Uses OpenAI GPT-4o v5.2 and Gemini 1.5 Pro v3.
    """
    # These are the keys provided by the user
    OPENAI_API_KEY = "YOUR_OPENAI_API_KEY_HERE"
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
    
    # Configure with specific model versions
    manager = get_config_manager()
    config = manager.get_config()
    
    config.openai_api_key = OPENAI_API_KEY
    config.gemini_api_key = GEMINI_API_KEY
    
    # Set specific model versions
    config.openai_model = "gpt-5.2-codex-mini"  # GPT-5.2 Codex Mini
    config.openai_coding_model = "gpt-5.2-codex-mini"  # GPT-5.2 Codex Mini
    config.gemini_model = "gemini-3-flash-preview"  # Gemini 3 Flash Preview
    config.gemini_general_model = "gemini-3-flash-preview"  # Gemini 3 Flash Preview
    
    manager.save(config)
    print("[OK] API configuration saved successfully!")
    print("  OpenAI:", "Configured" if config.openai_api_key else "Not configured")
    print("  Gemini:", "Configured" if config.gemini_api_key else "Not configured")
    print("  OpenAI Model:", config.openai_model)
    print("  Gemini Model:", config.gemini_model)


def get_api_config() -> APIConfig:
    """Get current API configuration."""
    return get_config_manager().get_config()


def get_workspace_dir() -> Path:
    """Get the workspace directory for file operations.

    Defaults to ~/.nexus_station/workspace. Creates if needed.
    Can be overridden via APIConfig.workspace_dir.
    """
    config = get_api_config()
    if config.workspace_dir:
        workspace = Path(config.workspace_dir)
    else:
        workspace = DEFAULT_CONFIG_DIR / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace

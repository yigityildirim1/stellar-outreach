"""
Narrative Agentic Coding Framework

A Python implementation of the Narrative Agentic Coding philosophy.
Treat AI not as a tool, but as a volatile CPU that needs an operating system.
"""

from .charter import Charter, Article
from .privilege import PrivilegeRing, Permission
from .crew import CrewMember, Crew
from .protocol import ResponseProtocol, SessionState
from .fiscal import Budget, Expenditure
from .precedent import Precedent, PrecedentLog
from .config import (
    APIConfig,
    ConfigManager,
    configure_apis,
    auto_configure_with_defaults,
    get_api_config,
    get_config_manager,
    get_workspace_dir,
)
from .api_clients import (
    APIRouter,
    APIRequest,
    APIResponse,
    TaskType,
    OpenAIClient,
    GeminiClient,
    APIError,
    create_clients_from_config,
    get_router,
)
from .agent_core import (
    NexusAgent,
    AgentResponse,
    CrewResponse,
    create_nexus_agent,
)
from .memory import (
    MemoryManager,
    get_memory_manager,
    Message,
    Task,
    CharacterMemory,
)
from .actions import (
    parse_actions,
    execute_actions,
    execute_confirmed_action,
    ActionResult,
    PendingAction,
    PendingActionStore,
    get_pending_store,
)

__version__ = "1.0.0"
__all__ = [
    # Core framework
    "Charter",
    "Article",
    "PrivilegeRing",
    "Permission",
    "CrewMember",
    "Crew",
    "ResponseProtocol",
    "SessionState",
    "Budget",
    "Expenditure",
    "Precedent",
    "PrecedentLog",
    # Configuration
    "APIConfig",
    "ConfigManager",
    "configure_apis",
    "auto_configure_with_defaults",
    "get_api_config",
    "get_config_manager",
    # API Clients
    "APIRouter",
    "APIRequest",
    "APIResponse",
    "TaskType",
    "OpenAIClient",
    "GeminiClient",
    "APIError",
    "create_clients_from_config",
    "get_router",
    # Agent Core
    "NexusAgent",
    "AgentResponse",
    "CrewResponse",
    "create_nexus_agent",
    # Memory
    "MemoryManager",
    "get_memory_manager",
    "Message",
    "Task",
    "CharacterMemory",
    # Actions
    "parse_actions",
    "execute_actions",
    "execute_confirmed_action",
    "ActionResult",
    "PendingAction",
    "PendingActionStore",
    "get_pending_store",
]

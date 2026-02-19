"""
Action Parser & Executor for NEXUS STATION.

Parses [ACTION:...] blocks from LLM output and executes them
against the memory manager (creating tasks, communications, etc.).

Also handles file operations (READ_FILE, WRITE_FILE) and code execution
(EXECUTE_CODE) with Article V confirmation gates for irreversible actions.
"""

import json
import os
import re
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import get_workspace_dir
from .memory import MemoryManager


# Regex to match [ACTION:TYPE]{json}[/ACTION]
ACTION_PATTERN = re.compile(
    r'\[ACTION:(CREATE_COMM|CREATE_TASK|READ_FILE|WRITE_FILE|EXECUTE_CODE)\](.*?)\[/ACTION\]',
    re.DOTALL
)

# Actions that require Director confirmation (Article V: Irreversibility Gate)
REQUIRES_CONFIRMATION = {"WRITE_FILE", "EXECUTE_CODE"}

# Dangerous command patterns blocked from EXECUTE_CODE
BLOCKED_COMMAND_PATTERNS = [
    r'\brm\s+-rf\s+/',
    r'\brm\s+-rf\s+~',
    r'\bmkfs\b',
    r'\bdd\s+if=',
    r'\bshutdown\b',
    r'\breboot\b',
    r'\bhalt\b',
    r'\binit\s+0\b',
    r'\bsystemctl\s+(poweroff|halt|reboot)\b',
    r':\(\)\s*\{\s*:\|:\s*&\s*\}\s*;',  # Fork bomb
    r'\bchmod\s+-R\s+777\s+/',
    r'\bchown\s+-R\s+.*\s+/',
    r'\b>\s*/dev/sd',
    r'\bcurl\b.*\|\s*sh',
    r'\bwget\b.*\|\s*sh',
]


@dataclass
class ActionResult:
    """Result of executing a single action."""
    success: bool
    action_type: str
    summary: str
    details: dict = field(default_factory=dict)


@dataclass
class PendingAction:
    """An action awaiting Director confirmation (Article V)."""
    id: str
    action_type: str
    params: dict
    proposed_at: float
    ttl: int = 300  # 5 minutes

    @property
    def expired(self) -> bool:
        return (time.time() - self.proposed_at) > self.ttl


class PendingActionStore:
    """Thread-safe in-memory store for pending actions."""

    def __init__(self):
        self._actions: dict[str, PendingAction] = {}
        self._lock = threading.Lock()

    def add(self, action: PendingAction) -> None:
        with self._lock:
            self._actions[action.id] = action

    def get(self, action_id: str) -> Optional[PendingAction]:
        with self._lock:
            self.cleanup_expired()
            return self._actions.get(action_id)

    def remove(self, action_id: str) -> Optional[PendingAction]:
        with self._lock:
            return self._actions.pop(action_id, None)

    def cleanup_expired(self) -> None:
        expired = [k for k, v in self._actions.items() if v.expired]
        for k in expired:
            del self._actions[k]


# Module-level singleton
_pending_store: Optional[PendingActionStore] = None


def get_pending_store() -> PendingActionStore:
    global _pending_store
    if _pending_store is None:
        _pending_store = PendingActionStore()
    return _pending_store


def parse_actions(llm_output: str) -> tuple[str, list[dict]]:
    """
    Parse [ACTION:...] blocks from LLM output.

    Returns:
        (cleaned_content, raw_actions) where cleaned_content has
        action blocks stripped out and raw_actions is a list of
        {"type": str, "params": dict} entries.
    """
    raw_actions = []

    for match in ACTION_PATTERN.finditer(llm_output):
        action_type = match.group(1)
        json_str = match.group(2).strip()

        try:
            params = json.loads(json_str)
        except json.JSONDecodeError:
            continue

        raw_actions.append({"type": action_type, "params": params})

    # Strip action blocks from content for display
    cleaned = ACTION_PATTERN.sub('', llm_output).strip()

    return cleaned, raw_actions


def execute_actions(
    raw_actions: list[dict], memory_manager: MemoryManager
) -> tuple[list[ActionResult], list[dict]]:
    """
    Execute parsed actions against the memory manager.

    Actions in REQUIRES_CONFIRMATION are queued as pending (not executed).

    Returns:
        (immediate_results, pending_actions_info)
    """
    results = []
    pending_info = []

    for action in raw_actions:
        action_type = action["type"]
        params = action["params"]

        if action_type in REQUIRES_CONFIRMATION:
            # Queue for Director confirmation (Article V)
            pending = PendingAction(
                id=str(uuid.uuid4())[:8],
                action_type=action_type,
                params=params,
                proposed_at=time.time(),
            )
            get_pending_store().add(pending)

            # Build summary for frontend
            if action_type == "WRITE_FILE":
                summary = f"Write file: {params.get('filepath', 'unknown')}"
            else:
                summary = f"Execute: {params.get('command', 'unknown')}"

            pending_info.append({
                "id": pending.id,
                "type": action_type,
                "params": params,
                "summary": summary,
            })
        elif action_type == "READ_FILE":
            result = _execute_read_file(params)
            results.append(result)
        elif action_type == "CREATE_COMM":
            result = _execute_create_comm(params, memory_manager)
            results.append(result)
        elif action_type == "CREATE_TASK":
            result = _execute_create_task(params, memory_manager)
            results.append(result)
        else:
            results.append(ActionResult(
                success=False,
                action_type=action_type,
                summary=f"Unknown action type: {action_type}",
            ))

    return results, pending_info


def execute_confirmed_action(action_id: str, memory_manager: MemoryManager) -> ActionResult:
    """Execute a previously pending action after Director confirmation."""
    store = get_pending_store()
    pending = store.get(action_id)

    if pending is None:
        return ActionResult(
            success=False,
            action_type="UNKNOWN",
            summary="Action not found or expired.",
        )

    if pending.expired:
        store.remove(action_id)
        return ActionResult(
            success=False,
            action_type=pending.action_type,
            summary="Action expired (TTL exceeded).",
        )

    # Remove from store before executing
    store.remove(action_id)

    if pending.action_type == "WRITE_FILE":
        return _execute_write_file(pending.params, memory_manager)
    elif pending.action_type == "EXECUTE_CODE":
        return _execute_code(pending.params, memory_manager)
    else:
        return ActionResult(
            success=False,
            action_type=pending.action_type,
            summary=f"Unknown confirmed action type: {pending.action_type}",
        )


# ═══════════════════════════════════════════════════════════════
# FILE & CODE EXECUTION HANDLERS
# ═══════════════════════════════════════════════════════════════


def _validate_path(filepath: str) -> Path:
    """Validate and resolve a filepath against the workspace directory.

    Raises ValueError on path traversal attempts.
    """
    workspace = get_workspace_dir()
    resolved = (workspace / filepath).resolve()

    # Prevent path traversal
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError:
        raise ValueError(f"Path traversal denied: {filepath}")

    return resolved


def _execute_read_file(params: dict) -> ActionResult:
    """Execute a READ_FILE action (immediate, no confirmation needed)."""
    filepath = params.get("filepath", "")
    if not filepath:
        return ActionResult(
            success=False,
            action_type="READ_FILE",
            summary="Missing required field: filepath",
        )

    try:
        resolved = _validate_path(filepath)

        if not resolved.exists():
            return ActionResult(
                success=False,
                action_type="READ_FILE",
                summary=f"File not found: {filepath}",
            )

        content = resolved.read_text(encoding="utf-8", errors="replace")

        # Truncate at 50k chars
        truncated = len(content) > 50000
        if truncated:
            content = content[:50000] + "\n\n... [TRUNCATED at 50,000 characters]"

        return ActionResult(
            success=True,
            action_type="READ_FILE",
            summary=f"Read file: {filepath} ({len(content)} chars)",
            details={
                "filepath": filepath,
                "content": content,
                "truncated": truncated,
            },
        )
    except ValueError as e:
        return ActionResult(
            success=False,
            action_type="READ_FILE",
            summary=str(e),
        )
    except Exception as e:
        return ActionResult(
            success=False,
            action_type="READ_FILE",
            summary=f"Failed to read file: {e}",
        )


def _execute_write_file(params: dict, memory_manager: MemoryManager) -> ActionResult:
    """Execute a WRITE_FILE action (called after confirmation)."""
    filepath = params.get("filepath", "")
    content = params.get("content", "")

    if not filepath:
        return ActionResult(
            success=False,
            action_type="WRITE_FILE",
            summary="Missing required field: filepath",
        )

    try:
        resolved = _validate_path(filepath)

        # Create parent directories
        resolved.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        resolved.write_text(content, encoding="utf-8")

        # Audit log via memory manager
        memory_manager.create_communication(
            subject=f"File Written: {filepath}",
            content=f"File written to workspace: {filepath}\nSize: {len(content)} chars",
            from_member="NEXUS",
            comm_type="UPDATE",
            priority="NORMAL",
        )

        return ActionResult(
            success=True,
            action_type="WRITE_FILE",
            summary=f"File written: {filepath} ({len(content)} chars)",
            details={
                "filepath": filepath,
                "size": len(content),
            },
        )
    except ValueError as e:
        return ActionResult(
            success=False,
            action_type="WRITE_FILE",
            summary=str(e),
        )
    except Exception as e:
        return ActionResult(
            success=False,
            action_type="WRITE_FILE",
            summary=f"Failed to write file: {e}",
        )


def _execute_code(params: dict, memory_manager: MemoryManager) -> ActionResult:
    """Execute an EXECUTE_CODE action (called after confirmation)."""
    command = params.get("command", "")
    working_dir = params.get("working_dir", "")
    timeout = min(params.get("timeout", 30), 60)  # Max 60 seconds

    if not command:
        return ActionResult(
            success=False,
            action_type="EXECUTE_CODE",
            summary="Missing required field: command",
        )

    # Check blocklist
    for pattern in BLOCKED_COMMAND_PATTERNS:
        if re.search(pattern, command):
            return ActionResult(
                success=False,
                action_type="EXECUTE_CODE",
                summary=f"Blocked: command matches dangerous pattern",
            )

    # Resolve working directory
    workspace = get_workspace_dir()
    if working_dir:
        try:
            cwd = _validate_path(working_dir)
        except ValueError as e:
            return ActionResult(
                success=False,
                action_type="EXECUTE_CODE",
                summary=str(e),
            )
    else:
        cwd = workspace

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "HOME": str(Path.home())},
        )

        stdout = result.stdout[:50000] if result.stdout else ""
        stderr = result.stderr[:50000] if result.stderr else ""

        # Audit log
        memory_manager.create_communication(
            subject=f"Code Executed: {command[:50]}",
            content=f"Command: {command}\nExit code: {result.returncode}\nOutput length: {len(stdout)} chars",
            from_member="NEXUS",
            comm_type="UPDATE",
            priority="NORMAL",
        )

        return ActionResult(
            success=result.returncode == 0,
            action_type="EXECUTE_CODE",
            summary=f"Executed: {command[:80]} (exit {result.returncode})",
            details={
                "command": command,
                "exit_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
            },
        )
    except subprocess.TimeoutExpired:
        return ActionResult(
            success=False,
            action_type="EXECUTE_CODE",
            summary=f"Timed out after {timeout}s: {command[:80]}",
        )
    except Exception as e:
        return ActionResult(
            success=False,
            action_type="EXECUTE_CODE",
            summary=f"Execution failed: {e}",
        )


# ═══════════════════════════════════════════════════════════════
# EXISTING COMM/TASK HANDLERS
# ═══════════════════════════════════════════════════════════════


def _execute_create_comm(params: dict, memory_manager: MemoryManager) -> ActionResult:
    """Execute a CREATE_COMM action."""
    subject = params.get("subject", "")
    content = params.get("content", "")
    from_member = params.get("from_member", "NEXUS")
    comm_type = params.get("type", "UPDATE")
    priority = params.get("priority", "NORMAL")

    if not subject or not content:
        return ActionResult(
            success=False,
            action_type="CREATE_COMM",
            summary="Missing required fields: subject and content",
        )

    try:
        comm = memory_manager.create_communication(
            subject=subject,
            content=content,
            from_member=from_member,
            comm_type=comm_type,
            priority=priority,
        )
        return ActionResult(
            success=True,
            action_type="CREATE_COMM",
            summary=f"Communication created: {comm.id} — \"{subject}\" from {from_member}",
            details={
                "id": comm.id,
                "subject": comm.subject,
                "from_member": comm.from_member,
                "type": comm.type,
                "priority": comm.priority,
            },
        )
    except Exception as e:
        return ActionResult(
            success=False,
            action_type="CREATE_COMM",
            summary=f"Failed to create communication: {e}",
        )


def _execute_create_task(params: dict, memory_manager: MemoryManager) -> ActionResult:
    """Execute a CREATE_TASK action."""
    title = params.get("title", "")
    description = params.get("description", "")
    assigned_to = params.get("assigned_to", "NEXUS")
    priority = params.get("priority", "MEDIUM")

    if not title:
        return ActionResult(
            success=False,
            action_type="CREATE_TASK",
            summary="Missing required field: title",
        )

    try:
        task = memory_manager.create_task(
            title=title,
            description=description,
            assigned_to=assigned_to,
            priority=priority,
        )
        return ActionResult(
            success=True,
            action_type="CREATE_TASK",
            summary=f"Task created: {task.id} — \"{title}\" assigned to {assigned_to}",
            details={
                "id": task.id,
                "title": task.title,
                "assigned_to": task.assigned_to,
                "priority": task.priority,
                "status": task.status,
            },
        )
    except Exception as e:
        return ActionResult(
            success=False,
            action_type="CREATE_TASK",
            summary=f"Failed to create task: {e}",
        )


# Instructions to append to system prompts so the LLM knows how to emit actions
ACTION_INSTRUCTIONS = """
═══════════════════════════════════════════════════════════
MANDATORY ACTION SYSTEM — YOU MUST USE THIS
═══════════════════════════════════════════════════════════

You have the ability to CREATE REAL DATA in the station's systems by including
action blocks in your response. The system parses and executes them automatically.

*** CRITICAL: When the Director asks you to do ANY of the following, you MUST
include the matching action block. Failure to include it means NOTHING gets created. ***

TRIGGER PHRASES → REQUIRED ACTION:
- "send me a report/message/comms" → YOU MUST include [ACTION:CREATE_COMM]
- "add to comms page" → YOU MUST include [ACTION:CREATE_COMM]
- "create a task" → YOU MUST include [ACTION:CREATE_TASK]
- "log this" / "record this" → YOU MUST include [ACTION:CREATE_COMM]
- "assign a task" → YOU MUST include [ACTION:CREATE_TASK]
- "create a file" / "write a file" / "save to file" → YOU MUST include [ACTION:WRITE_FILE]
- "run this" / "execute" / "run the code" / "run hello.py" → YOU MUST include [ACTION:EXECUTE_CODE]
- "read file" / "show file" / "cat file" → YOU MUST include [ACTION:READ_FILE]

FORMAT (copy exactly, replace values):

To send a report/message to the Comms page:
[ACTION:CREATE_COMM]{"subject":"Subject line here","content":"Full message body here","from_member":"Your Full Name","type":"REPORT","priority":"NORMAL"}[/ACTION]
   type options: REPORT, ALERT, UPDATE, RECOMMENDATION
   priority options: LOW, NORMAL, HIGH, URGENT

To create a task on the Mission Log:
[ACTION:CREATE_TASK]{"title":"Task title","description":"Task details","assigned_to":"Full Crew Name","priority":"MEDIUM"}[/ACTION]
   priority options: LOW, MEDIUM, HIGH, CRITICAL

To write/create a file (requires Director confirmation):
[ACTION:WRITE_FILE]{"filepath":"path/to/file.py","content":"file content here"}[/ACTION]
   filepath is relative to the workspace directory

To execute a command (requires Director confirmation):
[ACTION:EXECUTE_CODE]{"command":"python hello.py","working_dir":"","timeout":30}[/ACTION]
   command: the shell command to run
   working_dir: optional subdirectory within workspace (default: workspace root)
   timeout: max seconds (default 30, max 60)

To read a file (executes immediately, no confirmation needed):
[ACTION:READ_FILE]{"filepath":"path/to/file.py"}[/ACTION]
   filepath is relative to the workspace directory

RULES:
- Place action blocks at the END of your response, AFTER your conversational text
- You MUST include these blocks — without them, no data is created in the system
- You may include multiple action blocks in one response
- Always confirm to the Director in your conversational text what you are creating
- Use your full crew name as from_member (e.g. "Marina Okonkwo", "Professor James Whitmore")
- WRITE_FILE and EXECUTE_CODE require Director approval before execution (Article V)
- READ_FILE executes immediately (non-destructive)

EXAMPLE — if Director says "Marina, send me a test message":
Your conversational response here...
[ACTION:CREATE_COMM]{"subject":"Test Message","content":"Hello Director, this is a test communication from the station.","from_member":"Marina Okonkwo","type":"UPDATE","priority":"NORMAL"}[/ACTION]

EXAMPLE — if Director says "Create a hello.py file":
Your conversational response here...
[ACTION:WRITE_FILE]{"filepath":"hello.py","content":"print('Hello, World!')"}[/ACTION]

EXAMPLE — if Director says "Run hello.py":
Your conversational response here...
[ACTION:EXECUTE_CODE]{"command":"python hello.py"}[/ACTION]
═══════════════════════════════════════════════════════════
"""

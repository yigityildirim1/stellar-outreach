"""
Persistent Memory Module for NEXUS STATION.

Stores conversation history and character memories across sessions.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List


DEFAULT_MEMORY_DIR = Path.home() / ".nexus_station"
DEFAULT_MEMORY_FILE = DEFAULT_MEMORY_DIR / "memory.json"


@dataclass
class Message:
    """A single message in conversation history."""
    role: str  # "director", "nexus", "elena", "kai", "marina", "james"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    loop_number: int = 0


@dataclass
class CharacterMemory:
    """Memory for a specific character."""
    name: str
    relationship_notes: str = ""  # What the character remembers about the Director
    conversation_count: int = 0
    last_interaction: Optional[str] = None
    preferences: dict = field(default_factory=dict)  # Director's preferences
    
    def add_interaction(self, message: str) -> None:
        """Record a new interaction."""
        self.conversation_count += 1
        self.last_interaction = datetime.now().isoformat()


@dataclass
class Communication:
    """A communication/message from a crew member (email-like)."""
    id: str
    subject: str
    content: str
    from_member: str  # Character name
    type: str = "UPDATE"  # REPORT, ALERT, UPDATE, RECOMMENDATION
    priority: str = "NORMAL"  # LOW, NORMAL, HIGH, URGENT
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    read: bool = False
    starred: bool = False


@dataclass
class Task:
    """A task assigned to a character (Jira-like)."""
    id: str
    title: str
    description: str
    assigned_to: str  # Character name
    status: str = "OPEN"  # OPEN, IN_PROGRESS, REVIEW, DONE, CANCELLED
    priority: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    comments: List[dict] = field(default_factory=list)
    
    def update_status(self, new_status: str) -> None:
        self.status = new_status
        self.updated_at = datetime.now().isoformat()
        if new_status == "DONE":
            self.completed_at = datetime.now().isoformat()
    
    def add_comment(self, author: str, content: str) -> None:
        self.comments.append({
            "author": author,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })


@dataclass
class Memory:
    """Complete memory for NEXUS STATION."""
    # Global conversation history
    global_history: List[Message] = field(default_factory=list)
    
    # Per-character conversation history
    character_histories: dict[str, List[Message]] = field(default_factory=lambda: {
        "elena": [],
        "kai": [],
        "marina": [],
        "james": [],
    })
    
    # Character memories (what each character remembers about the Director)
    character_memories: dict[str, CharacterMemory] = field(default_factory=lambda: {
        "elena": CharacterMemory(name="Dr. Elena Vasquez"),
        "kai": CharacterMemory(name="Kai Chen"),
        "marina": CharacterMemory(name="Marina Okonkwo"),
        "james": CharacterMemory(name="Professor James Whitmore"),
    })
    
    # Task tracking (Jira-like)
    tasks: List[Task] = field(default_factory=list)
    task_counter: int = 0

    # Communications (email-like)
    communications: List[Communication] = field(default_factory=list)
    comm_counter: int = 0

    # Session tracking
    total_sessions: int = 0
    last_session_date: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert memory to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Memory":
        """Create memory from dictionary."""
        # Reconstruct nested dataclasses
        memory = cls()
        
        if "global_history" in data:
            memory.global_history = [Message(**m) for m in data["global_history"]]
        
        if "character_histories" in data:
            for char, hist in data["character_histories"].items():
                memory.character_histories[char] = [Message(**m) for m in hist]
        
        if "character_memories" in data:
            for char, mem in data["character_memories"].items():
                memory.character_memories[char] = CharacterMemory(**mem)
        
        if "tasks" in data:
            memory.tasks = [Task(**t) for t in data["tasks"]]

        if "communications" in data:
            memory.communications = [Communication(**c) for c in data["communications"]]

        memory.task_counter = data.get("task_counter", 0)
        memory.comm_counter = data.get("comm_counter", 0)
        memory.total_sessions = data.get("total_sessions", 0)
        memory.last_session_date = data.get("last_session_date")
        
        return memory


class MemoryManager:
    """
    Manages persistent memory for NEXUS STATION.
    
    Stores conversation history, character memories, and task tracking.
    """
    
    def __init__(self, memory_path: Optional[Path] = None):
        self.memory_path = memory_path or DEFAULT_MEMORY_FILE
        self._memory: Optional[Memory] = None
    
    def _ensure_memory_dir(self) -> None:
        """Ensure the memory directory exists."""
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> Memory:
        """Load memory from file."""
        if self._memory is not None:
            return self._memory
        
        if self.memory_path.exists():
            try:
                with open(self.memory_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._memory = Memory.from_dict(data)
            except (json.JSONDecodeError, TypeError) as e:
                print(f"[WARNING] Could not load memory: {e}")
                self._memory = Memory()
        else:
            self._memory = Memory()
        
        return self._memory
    
    def save(self, memory: Optional[Memory] = None) -> None:
        """Save memory to file."""
        if memory is None:
            memory = self._memory
        if memory is None:
            raise ValueError("No memory to save")
        
        self._ensure_memory_dir()
        
        with open(self.memory_path, 'w', encoding='utf-8') as f:
            json.dump(memory.to_dict(), f, indent=2, ensure_ascii=False)
        
        self._memory = memory
    
    def get_memory(self) -> Memory:
        """Get current memory (loads if needed)."""
        if self._memory is None:
            return self.load()
        return self._memory
    
    def add_global_message(self, role: str, content: str, loop_number: int = 0) -> None:
        """Add a message to global history."""
        memory = self.get_memory()
        memory.global_history.append(Message(
            role=role,
            content=content,
            loop_number=loop_number,
        ))
        # Keep only last 100 messages
        memory.global_history = memory.global_history[-100:]
        self.save(memory)
    
    def add_character_message(self, character: str, role: str, content: str, loop_number: int = 0) -> None:
        """Add a message to character-specific history."""
        memory = self.get_memory()
        character = character.lower()
        if character in memory.character_histories:
            memory.character_histories[character].append(Message(
                role=role,
                content=content,
                loop_number=loop_number,
            ))
            # Keep only last 50 messages per character
            memory.character_histories[character] = memory.character_histories[character][-50:]
            
            # Update character memory
            if role == "director":
                memory.character_memories[character].add_interaction(content)
            
            self.save(memory)
    
    def get_character_history(self, character: str) -> List[Message]:
        """Get conversation history for a specific character."""
        memory = self.get_memory()
        return memory.character_histories.get(character.lower(), [])
    
    def get_character_memory(self, character: str) -> CharacterMemory:
        """Get memory for a specific character."""
        memory = self.get_memory()
        char_key = character.lower()
        if char_key not in memory.character_memories:
            memory.character_memories[char_key] = CharacterMemory(name=character)
        return memory.character_memories[char_key]
    
    def create_task(self, title: str, description: str, assigned_to: str, priority: str = "MEDIUM") -> Task:
        """Create a new task (Jira-like)."""
        memory = self.get_memory()
        memory.task_counter += 1
        
        task = Task(
            id=f"TASK-{memory.task_counter:03d}",
            title=title,
            description=description,
            assigned_to=assigned_to,
            priority=priority,
        )
        
        memory.tasks.append(task)
        self.save(memory)
        return task
    
    def get_tasks(self, assigned_to: Optional[str] = None, status: Optional[str] = None) -> List[Task]:
        """Get tasks with optional filtering."""
        memory = self.get_memory()
        tasks = memory.tasks
        
        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to.lower() == assigned_to.lower()]
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)
    
    def update_task_status(self, task_id: str, new_status: str) -> Optional[Task]:
        """Update task status."""
        memory = self.get_memory()
        for task in memory.tasks:
            if task.id == task_id:
                task.update_status(new_status)
                self.save(memory)
                return task
        return None

    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID."""
        memory = self.get_memory()
        original_len = len(memory.tasks)
        memory.tasks = [t for t in memory.tasks if t.id != task_id]
        if len(memory.tasks) < original_len:
            self.save(memory)
            return True
        return False

    def delete_all_tasks(self) -> int:
        """Delete all tasks. Returns count of deleted tasks."""
        memory = self.get_memory()
        count = len(memory.tasks)
        memory.tasks = []
        memory.task_counter = 0
        self.save(memory)
        return count
    
    def create_communication(self, subject: str, content: str, from_member: str,
                               comm_type: str = "UPDATE", priority: str = "NORMAL") -> Communication:
        """Create a new communication (email-like)."""
        memory = self.get_memory()
        memory.comm_counter += 1

        comm = Communication(
            id=f"COMM-{memory.comm_counter:03d}",
            subject=subject,
            content=content,
            from_member=from_member,
            type=comm_type,
            priority=priority,
        )

        memory.communications.append(comm)
        self.save(memory)
        return comm

    def get_communications(self, unread_only: bool = False, from_member: Optional[str] = None) -> List[Communication]:
        """Get communications with optional filtering."""
        memory = self.get_memory()
        comms = memory.communications

        if unread_only:
            comms = [c for c in comms if not c.read]

        if from_member:
            comms = [c for c in comms if c.from_member.lower() == from_member.lower()]

        return sorted(comms, key=lambda c: c.timestamp, reverse=True)

    def mark_communication_read(self, comm_id: str) -> Optional[Communication]:
        """Mark a communication as read."""
        memory = self.get_memory()
        for comm in memory.communications:
            if comm.id == comm_id:
                comm.read = True
                self.save(memory)
                return comm
        return None

    def toggle_communication_starred(self, comm_id: str) -> Optional[Communication]:
        """Toggle starred status of a communication."""
        memory = self.get_memory()
        for comm in memory.communications:
            if comm.id == comm_id:
                comm.starred = not comm.starred
                self.save(memory)
                return comm
        return None

    def start_new_session(self) -> None:
        """Mark the start of a new session."""
        memory = self.get_memory()
        memory.total_sessions += 1
        memory.last_session_date = datetime.now().isoformat()
        self.save(memory)
    
    def get_session_info(self) -> dict:
        """Get session information."""
        memory = self.get_memory()
        return {
            "total_sessions": memory.total_sessions,
            "last_session": memory.last_session_date,
            "total_global_messages": len(memory.global_history),
            "total_tasks": len(memory.tasks),
            "open_tasks": len([t for t in memory.tasks if t.status in ["OPEN", "IN_PROGRESS"]]),
        }


# Global memory manager instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get the global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
